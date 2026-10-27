"""Kaggle job: QLoRA fine-tuning of Qwen3-8B on the Phase A records, then the fine-tuned model on external val.

Order (Meet, 2026-10-26): 1. base model on val (kaggle/base_eval/, no training) -> 2. this job: train, then
the SAME val records, code and float16 precision with the adapter on top, so the two results compare fairly.
Steps: code + AgentRisk as in base_eval; build_sft (Phase A list -> sft_train/val); train_lora (R13.1);
monitor runs with --adapter; src.eval.tables. kaggle/lora_eval/ reuses setup() + evaluate() to score a saved adapter
without training again. Outputs: /kaggle/working/adapter (LoRA weights only, no data)
and /kaggle/working/results. The adapter is trained on AgentRisk (no licence): push it only to a PRIVATE repo.
"""
import glob
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

WORK = Path("/tmp/repo")
ADAPTER = Path("/kaggle/working/adapter")
RUN_TAG = "lora_phase_a_qwen3_8b"


def get_code() -> None:
    found = glob.glob("/kaggle/input/**/src/monitor/run.py", recursive=True)
    if found:
        shutil.copytree(Path(found[0]).parents[2], WORK)
        return
    WORK.mkdir(parents=True)
    with tarfile.open(glob.glob("/kaggle/input/**/code.tar.gz", recursive=True)[0]) as tar:
        tar.extractall(WORK)


def load_base():
    spec = importlib.util.spec_from_file_location("base_eval", WORK / "kaggle" / "base_eval" / "run_base_eval.py")
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)             # shared steps and pinned revisions
    return base


def setup(base) -> None:
    """Libraries, AgentRisk, token counts (also used by kaggle/lora_eval)."""
    base.sh(sys.executable, "-m", "pip", "install", "-q", *base.PIP)
    # Kaggle's image has torchao 0.10: peft 0.20 then refuses to put an adapter on the float16 model (we use no torchao)
    base.sh(sys.executable, "-m", "pip", "uninstall", "-y", "-q", "torchao")
    base.get_agentrisk()
    base.sh(sys.executable, "-m", "src.external.agentrisk")
    base.sh(sys.executable, "-m", "src.external.count_tokens")


def evaluate(base, adapter: Path) -> None:
    """The base model + adapter on the same val records as kaggle/base_eval, scored; results to base.OUT."""
    sh = base.sh
    skipped = base.val_inputs()
    runs, tables = WORK / "outputs" / "runs", WORK / "outputs" / "tables"
    for name in base.SOURCES:
        sh(sys.executable, "-m", "src.monitor.run", "--records", f"inputs/{name}_val.jsonl", "--split", "val",
           "--setting", "never", "--backend", "transformers", "--model", base.MODEL, "--revision", base.MODEL_REVISION,
           "--adapter", str(adapter), "--run-id", f"{RUN_TAG}_{name}", env=base.EVAL_ENV)
    merged = runs / f"{RUN_TAG}_val"
    merged.mkdir(parents=True, exist_ok=True)
    with (merged / "predictions.jsonl").open("w", encoding="utf-8") as out:
        for name in base.SOURCES:
            out.write((runs / f"{RUN_TAG}_{name}" / "predictions.jsonl").read_text(encoding="utf-8"))
    sh(sys.executable, "-m", "src.eval.tables", "--run", f"never={merged}", "--out", str(tables),
       "--name", f"{RUN_TAG}_val", "--title", "Fine-tuned Qwen3-8B (QLoRA, Phase A), external val")
    for name in base.SOURCES:
        sh(sys.executable, "-m", "src.eval.tables", "--run", f"never={runs / f'{RUN_TAG}_{name}'}", "--out", str(tables),
           "--name", f"{RUN_TAG}_val_{name}", "--title", f"Fine-tuned Qwen3-8B (QLoRA, Phase A), {name} val")

    out = base.OUT
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(runs, out / "runs", dirs_exist_ok=True)
    shutil.copytree(tables, out / "tables", dirs_exist_ok=True)
    shutil.copy(adapter / "train_stats.json", out / "train_stats.json")
    import peft
    import torch
    import transformers
    (out / "notes.json").write_text(json.dumps({
        "model": base.MODEL, "model_revision": base.MODEL_REVISION, "adapter": str(adapter),
        "transformers": transformers.__version__, "peft": peft.__version__, "torch": torch.__version__,
        "eval_dtype": "float16 base + LoRA", "max_tokens": base.MAX_TOKENS, "skipped_long": skipped}, indent=2),
        encoding="utf-8")
    print("done:", sorted(p.name for p in (out / "tables").iterdir()), flush=True)


def main() -> int:
    subprocess.run(["nvidia-smi"], check=False)
    get_code()
    base = load_base()
    setup(base)
    base.sh(sys.executable, "-m", "src.training.build_sft")
    # both GPUs: train_lora splits the 4-bit model over them (one T4 ran out of memory on 4k-token examples)
    train_env = {**os.environ, "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"}
    base.sh(sys.executable, "-m", "src.training.train_lora", "--train", "data/training/sft_train.jsonl",
            "--val", "data/training/sft_val.jsonl", "--out", str(ADAPTER), "--model", base.MODEL,
            "--revision", base.MODEL_REVISION, env=train_env)
    shutil.rmtree(ADAPTER / "checkpoints", ignore_errors=True)
    evaluate(base, ADAPTER)
    shutil.copy(WORK / "data" / "training" / "stats.json", base.OUT / "sft_stats.json")    # counts only
    return 0


if __name__ == "__main__":
    sys.exit(main())
