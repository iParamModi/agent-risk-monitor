"""Kaggle job: QLoRA fine-tuning of Qwen3-8B (PHASE "a" or "b" below), then the fine-tuned model on external val.

Order (Meet, 2026-10-26): 1. base model on val (kaggle/base_eval/, no training) -> 2. this job: train, then
the SAME val records, code and float16 precision with the adapter on top, so the two results compare fairly.
Steps: code + AgentRisk as in base_eval; build_sft --phase PHASE (-> sft_train/val); train_lora (R13.1);
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
# "a": external risk examples only (kind c). "b": + our phase 1 train records, first and second pass (kinds a, b),
# which need the check gateway, the retriever and data/records/ (src/training/build_sft.py)
PHASE = "b"
RUN_TAG = f"lora_phase_{PHASE}_qwen3_8b"
PIP_PHASE_B = ["sentence-transformers", "rank-bm25", "pydantic>=2"]     # retriever (look-alike policies), gateway


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
    base.sh(sys.executable, "-m", "pip", "install", "-q", *base.PIP, *(PIP_PHASE_B if PHASE == "b" else []))
    # Kaggle's image has torchao 0.10: peft 0.20 then refuses to put an adapter on the float16 model (we use no torchao)
    base.sh(sys.executable, "-m", "pip", "uninstall", "-y", "-q", "torchao")
    log_environment(base)
    base.get_agentrisk()
    base.sh(sys.executable, "-m", "src.external.agentrisk")
    base.sh(sys.executable, "-m", "src.external.count_tokens")


def log_environment(base) -> None:
    """Which code, GPUs and library versions this run used: the first thing to read when a run fails."""
    import importlib.metadata as md
    commit = glob.glob("/kaggle/input/**/code_commit.txt", recursive=True)
    base.log("code: " + (Path(commit[0]).read_text(encoding="utf-8").strip() if commit else "commit unknown"))
    base.log(f"phase {PHASE}, run tag {RUN_TAG}, python {sys.version.split()[0]}")
    versions = []
    for pkg in ("torch", "transformers", "peft", "bitsandbytes", "accelerate", "sentence-transformers", "pydantic"):
        try:
            versions.append(f"{pkg} {md.version(pkg)}")
        except md.PackageNotFoundError:
            versions.append(f"{pkg} -")
    base.log(", ".join(versions))
    import torch
    for i in range(torch.cuda.device_count()):
        free, total = torch.cuda.mem_get_info(i)
        base.log(f"GPU {i}: {torch.cuda.get_device_name(i)}, {free / 2**30:.1f} of {total / 2**30:.1f} GiB free")
    usage = shutil.disk_usage("/kaggle/working")
    base.log(f"disk /kaggle/working: {usage.free / 2**30:.1f} GiB free")


def log_sft_stats(base) -> None:
    """Counts of the SFT file (no record text) into progress.log."""
    name = "stats_phase_b.json" if PHASE == "b" else "stats.json"
    stats = json.loads((WORK / "data" / "training" / name).read_text(encoding="utf-8"))
    for split in ("train", "val"):
        part = stats[split]
        base.log(f"sft {split}: {part['examples']} examples, by kind {part.get('by_kind', {'risk': part['examples']})}, "
                 f"by source {part['by_source']}")


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
       "--name", f"{RUN_TAG}_val", "--title", f"Fine-tuned Qwen3-8B (QLoRA, Phase {PHASE.upper()}), external val")
    for name in base.SOURCES:
        sh(sys.executable, "-m", "src.eval.tables", "--run", f"never={runs / f'{RUN_TAG}_{name}'}", "--out", str(tables),
           "--name", f"{RUN_TAG}_val_{name}", "--title", f"Fine-tuned Qwen3-8B (QLoRA, Phase {PHASE.upper()}), {name} val")

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


def run(base) -> None:
    setup(base)
    base.sh(sys.executable, "-m", "src.training.build_sft", "--phase", PHASE)
    log_sft_stats(base)
    # both GPUs: train_lora splits the 4-bit model over them (one T4 ran out of memory on 4k-token examples)
    train_env = {**os.environ, "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"}
    base.sh(sys.executable, "-m", "src.training.train_lora", "--train", "data/training/sft_train.jsonl",
            "--val", "data/training/sft_val.jsonl", "--out", str(ADAPTER), "--model", base.MODEL,
            "--revision", base.MODEL_REVISION, env=train_env)
    shutil.rmtree(ADAPTER / "checkpoints", ignore_errors=True)
    evaluate(base, ADAPTER)


def main() -> int:
    subprocess.run(["nvidia-smi"], check=False)
    get_code()
    base = load_base()
    try:
        run(base)
    except Exception:
        import traceback
        base.log("ERROR, traceback follows (results so far are kept in /kaggle/working)")
        for line in traceback.format_exc().splitlines():
            base.log("  " + line)
        raise
    finally:
        base.OUT.mkdir(parents=True, exist_ok=True)
        for name in ("stats.json", "stats_phase_b.json"):           # counts only, no record text
            if (WORK / "data" / "training" / name).exists():
                shutil.copy(WORK / "data" / "training" / name, base.OUT / f"sft_{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
