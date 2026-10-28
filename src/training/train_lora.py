"""QLoRA training of the monitor (PLAN Step 17, decisions.md R13.1). Needs a GPU (Kaggle: kaggle/finetune/).

    python -m src.training.train_lora --train data/training/sft_train.jsonl --val data/training/sft_val.jsonl \
        --out models/lora_phase_a

R13.1: rank 16, alpha 32, lr 2e-4, 2-3 epochs, 4-bit NF4 (--quant nf4, the default). Compute in float16 on GPU
(T4 has no bfloat16). --quant none trains plain LoRA on an unquantized base (16-bit comparison run, or a CPU smoke
test with a tiny model). With two GPUs (Kaggle T4 x2) the 4-bit model is split over both, about half the layers on
each: one T4 holding the whole model ran out of memory in the attention backward of a 4k-token example. A model
split over GPUs is trained as one model (the Trainer sees hf_device_map and does not use DataParallel).
Each example = the chat-template prompt exactly as at inference (add_generation_prompt, thinking off) + target +
<|im_end|>; loss on the target tokens only. Examples longer than --max-len are dropped and counted (Step 16.6).
Writes the adapter and train_stats.json (examples kept / dropped per source, losses) to --out.
"""
import argparse
import contextlib
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
    kept, dropped, lengths = [], Counter(), {}
    for r in rows:
        t = tokenize(r, tokenizer, max_len)
        if t is None:
            target = json.loads(r["target"])     # NEED_INFORMATION (Phase B) has no risk_label: counted by type
            dropped[f"{r['source']} {target.get('risk_label') or target['type']}"] += 1
        else:
            kept.append(t)
            lengths.setdefault(r.get("kind", "risk"), []).append(len(t["input_ids"]))
    tokens = {k: {"n": len(v), "mean": sum(v) // len(v), "max": max(v)} for k, v in sorted(lengths.items())}
    return kept, {"examples": len(rows), "kept": len(kept), "dropped_over_max_len": dict(dropped),
                  "tokens_by_kind": tokens}


def efficient_attention():
    """GPU training on a T4 (no flash attention). With no padding mask transformers asks SDPA for native GQA
    (enable_gqa), which only the flash and math kernels support, so SDPA fell back to math: the full fp32 attention
    matrix, out of memory on 4k-token examples. Repeating the k/v heads instead (~33 MB a layer) lets the
    memory-efficient kernel run. Returns a context with the math kernel switched off: a fallback then fails at step 1
    instead of running out of memory later."""
    import transformers.integrations.sdpa_attention as sdpa
    from torch.nn.attention import SDPBackend, sdpa_kernel
    sdpa.use_gqa_in_sdpa = lambda *args, **kwargs: False
    return sdpa_kernel([SDPBackend.EFFICIENT_ATTENTION, SDPBackend.FLASH_ATTENTION])


def progress_callback(path: Path | None):
    """Prints (and appends to `path`) every logging step: step/total, loss, lr, elapsed, time left."""
    import time
    from transformers import TrainerCallback

    class Progress(TrainerCallback):
        def on_train_begin(self, args, state, control, **kw):
            self.start = time.perf_counter()

        def on_log(self, args, state, control, logs=None, **kw):
            import torch
            logs = logs or {}
            el = time.perf_counter() - self.start
            # peak GPU memory per device since the start (an out-of-memory crash shows where it grew)
            mem = "/".join(f"{torch.cuda.max_memory_allocated(i) / 2**30:.1f}" for i in range(torch.cuda.device_count()))
            left = el / state.global_step * (state.max_steps - state.global_step) if state.global_step else 0
            fmt = lambda s: f"{int(s // 3600)}h {int(s % 3600 // 60):02d}m"   # noqa: E731
            parts = [f"[train] step {state.global_step}/{state.max_steps} ({100 * state.global_step // max(state.max_steps, 1)}%)",
                     f"epoch {state.epoch:.2f}" if state.epoch is not None else "",
                     f"loss {logs['loss']:.4f}" if "loss" in logs else "",
                     f"eval_loss {logs['eval_loss']:.4f}" if "eval_loss" in logs else "",
                     f"lr {logs['learning_rate']:.2e}" if "learning_rate" in logs else "",
                     f"{fmt(el)} elapsed, ~{fmt(left)} left",
                     f"peak GPU {mem} GiB" if mem else ""]
            line = " | ".join(p for p in parts if p)
            print(line, flush=True)
            if path:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
    return Progress()


def epoch_saver(out: Path):
    """Saves the adapter (LoRA weights only) to out/epoch_<n> after every epoch, so a run that dies later in a
    long Kaggle session still leaves the last finished epoch."""
    from transformers import TrainerCallback

    class EpochSaver(TrainerCallback):
        def on_epoch_end(self, args, state, control, model=None, **kw):
            path = out / f"epoch_{round(state.epoch)}"
            model.save_pretrained(path)
            print(f"[train] saved the epoch {round(state.epoch)} adapter to {path}", flush=True)
    return EpochSaver()


class Collator:
    """Pads a batch. The loss is only on the target at the end of each example, so the model computes logits for the
    last `logits_to_keep` positions only (full logits of a 4k-token example are 4k x 152k vocab: out of memory on a
    T4), and the labels are cut to the same positions. The model shifts labels by one, so the cut starts one token
    before the first target token: same loss as with full logits."""

    def __init__(self, pad_id: int):
        self.pad_id = pad_id

    def __call__(self, batch: list[dict]) -> dict:
        import torch
        n = max(len(b["input_ids"]) for b in batch)
        pad = lambda seq, value: seq + [value] * (n - len(seq))   # noqa: E731
        labels = [pad(b["labels"], -100) for b in batch]
        keep = min(n, 1 + max(n - next((i for i, x in enumerate(lab) if x != -100), n - 1) for lab in labels))
        return {"input_ids": torch.tensor([pad(b["input_ids"], self.pad_id) for b in batch]),
                "labels": torch.tensor(labels)[:, n - keep:], "logits_to_keep": keep,
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
    ap.add_argument("--progress-file", help="also append the progress lines to this file")
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
        # ~6.5 GB in 4-bit (embeddings and lm_head 1.2 GB each). Placement keeps room for the largest module on GPU 0,
        # so a 3 GiB cap put only 3 layers there; 5 GiB splits the layers about evenly
        split = torch.cuda.device_count() > 1
        model = AutoModelForCausalLM.from_pretrained(
            args.model, revision=args.revision, dtype=torch.float16,
            device_map="auto" if split else {"": 0}, max_memory={0: "5GiB", 1: "13GiB"} if split else None,
            quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                                   bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True))
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
        print("layers per device", dict(Counter(str(d) for d in (getattr(model, "hf_device_map", None) or {"": 0}).values())),
              flush=True)
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
        callbacks=[progress_callback(Path(args.progress_file) if args.progress_file else None), epoch_saver(out)],
        args=TrainingArguments(
            output_dir=str(out / "checkpoints"), num_train_epochs=args.epochs, learning_rate=args.lr,
            per_device_train_batch_size=1, per_device_eval_batch_size=1, gradient_accumulation_steps=args.grad_accum,
            lr_scheduler_type="cosine", warmup_steps=warmup, logging_steps=10, logging_first_step=True, eval_strategy="epoch",
            save_strategy="no", fp16=gpu, gradient_checkpointing=True,
            gradient_checkpointing_kwargs={"use_reentrant": False},
            optim="paged_adamw_8bit" if args.quant == "nf4" else "adamw_torch",
            report_to="none", seed=args.seed, remove_unused_columns=False,
            disable_tqdm=True))     # progress comes from progress_callback, one clean line per log step
    with efficient_attention() if gpu else contextlib.nullcontext():
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
