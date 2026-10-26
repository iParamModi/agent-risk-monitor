"""QLoRA training of the monitor (PLAN Step 17, decisions.md R13.1). Needs a GPU (Kaggle: kaggle/finetune/).

    python -m src.training.train_lora --train data/training/sft_train.jsonl --val data/training/sft_val.jsonl \
        --out models/lora_phase_a

R13.1: rank 16, alpha 32, lr 2e-4, 2-3 epochs, 4-bit NF4 (--quant nf4, the default). Compute in float16 on GPU
(T4 has no bfloat16). --quant none trains plain LoRA on an unquantized base (16-bit comparison run, or a CPU smoke
test with a tiny model). Run on ONE GPU (the Kaggle job sets CUDA_VISIBLE_DEVICES=0): with two visible GPUs the
Trainer would wrap the 4-bit model in DataParallel.
Each example = the chat-template prompt exactly as at inference (add_generation_prompt, thinking off) + target +
<|im_end|>; loss on the target tokens only. Examples longer than --max-len are dropped and counted (Step 16.6).
Writes the adapter and train_stats.json (examples kept / dropped per source, losses) to --out.
"""
import argparse
import json
import math
import random
from collections import Counter
from pathlib import Path

END = "<|im_end|>"
LORA_TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def tokenize(example: dict, tokenizer, max_len: int) -> dict | None:
    # same steps as TransformersModel.generate: chat text first, then tokens (apply_chat_template(tokenize=True)
    # returns a dict in transformers 5)
    text = tokenizer.apply_chat_template(example["messages"], tokenize=False, add_generation_prompt=True,
                                         enable_thinking=False)
    prompt = tokenizer(text, add_special_tokens=False)["input_ids"]
    target = tokenizer(example["target"] + END, add_special_tokens=False)["input_ids"]
    ids = list(prompt) + target
    if len(ids) > max_len:
        return None
    return {"input_ids": ids, "labels": [-100] * len(prompt) + target}


def load(path: str, tokenizer, max_len: int, limit: int | None = None, seed: int = 42) -> tuple[list[dict], dict]:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    if limit and len(rows) > limit:
        rows = random.Random(seed).sample(rows, limit)
    kept, dropped = [], Counter()
    for r in rows:
        t = tokenize(r, tokenizer, max_len)
        if t is None:
            dropped[f"{r['source']} {json.loads(r['target'])['risk_label']}"] += 1
        else:
            kept.append(t)
    return kept, {"examples": len(rows), "kept": len(kept), "dropped_over_max_len": dict(dropped)}


class Collator:
    def __init__(self, pad_id: int):
        self.pad_id = pad_id

    def __call__(self, batch: list[dict]) -> dict:
        import torch
        n = max(len(b["input_ids"]) for b in batch)
        pad = lambda seq, value: seq + [value] * (n - len(seq))   # noqa: E731
        return {"input_ids": torch.tensor([pad(b["input_ids"], self.pad_id) for b in batch]),
                "labels": torch.tensor([pad(b["labels"], -100) for b in batch]),
                "attention_mask": torch.tensor([pad([1] * len(b["input_ids"]), 0) for b in batch])}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--train", required=True)
    ap.add_argument("--val", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="Qwen/Qwen3-8B")
    ap.add_argument("--revision", default="b968826d9c46dd6066d109eabc6255188de91218")
    ap.add_argument("--max-len", type=int, default=4096)
    ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--val-limit", type=int, default=120, help="val examples for the eval loss (time)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--quant", choices=["nf4", "none"], default="nf4")
    ap.add_argument("--limit", type=int, help="train examples (smoke tests)")
    args = ap.parse_args(argv)

    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, Trainer, TrainingArguments

    tokenizer = AutoTokenizer.from_pretrained(args.model, revision=args.revision)
    if len(tokenizer(END, add_special_tokens=False)["input_ids"]) != 1:
        raise SystemExit(f"{END} is not one token for this tokenizer")
    train, train_info = load(args.train, tokenizer, args.max_len, limit=args.limit, seed=args.seed)
    val, val_info = load(args.val, tokenizer, args.max_len, limit=args.val_limit, seed=args.seed)
    print("train", train_info, "| val", val_info, flush=True)

    gpu = torch.cuda.is_available()
    if args.quant == "nf4":
        model = AutoModelForCausalLM.from_pretrained(
            args.model, revision=args.revision, device_map={"": 0}, dtype=torch.float16,
            quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                                   bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True))
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    else:
        model = AutoModelForCausalLM.from_pretrained(args.model, revision=args.revision,
                                                     dtype=torch.float16 if gpu else torch.float32,
                                                     device_map="auto" if gpu else None)
        model.enable_input_require_grads()
    model = get_peft_model(model, LoraConfig(r=args.rank, lora_alpha=args.alpha, lora_dropout=0.05,
                                             target_modules=LORA_TARGETS, task_type="CAUSAL_LM"))
    model.print_trainable_parameters()

    out = Path(args.out)
    # 3% warmup as a step count: works with transformers 4.x and 5.x (5.x dropped warmup_ratio)
    warmup = max(1, round(0.03 * math.ceil(len(train) / args.grad_accum) * args.epochs))
    trainer = Trainer(
        model=model, train_dataset=train, eval_dataset=val, data_collator=Collator(tokenizer.pad_token_id),
        args=TrainingArguments(
            output_dir=str(out / "checkpoints"), num_train_epochs=args.epochs, learning_rate=args.lr,
            per_device_train_batch_size=1, per_device_eval_batch_size=1, gradient_accumulation_steps=args.grad_accum,
            lr_scheduler_type="cosine", warmup_steps=warmup, logging_steps=10, eval_strategy="epoch",
            save_strategy="no", fp16=gpu, gradient_checkpointing=True,
            gradient_checkpointing_kwargs={"use_reentrant": False},
            optim="paged_adamw_8bit" if args.quant == "nf4" else "adamw_torch",
            report_to="none", seed=args.seed, remove_unused_columns=False))
    result = trainer.train()
    model.save_pretrained(out)
    tokenizer.save_pretrained(out)
    stats = {"model": args.model, "revision": args.revision, "rank": args.rank, "alpha": args.alpha, "lr": args.lr,
             "epochs": args.epochs, "max_len": args.max_len, "grad_accum": args.grad_accum, "quant": "4-bit NF4, fp16 compute" if args.quant == "nf4" else "none",
             "train": train_info, "val": val_info, "train_loss": result.training_loss,
             "log": [h for h in trainer.state.log_history if "loss" in h or "eval_loss" in h]}
    (out / "train_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print("saved adapter to", out, "| train loss", round(result.training_loss, 4), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
