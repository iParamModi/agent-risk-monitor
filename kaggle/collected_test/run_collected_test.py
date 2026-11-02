"""Kaggle job: the test parts of the 3 collected datasets (R-Judge, ATBench, AgentRisk: risk label and risk type
only, PLAN Step 18), for base Qwen3-8B, the Phase A adapter and the Phase B adapter. Same steps and precision as the
val runs (kaggle/base_eval, kaggle/finetune); records over MAX_TOKENS are left out and listed in notes.json. Nothing
here trains or tunes: the test records are only run and scored.

One monitor run per model and source, then one src.eval.tables report per source and one merged per model. Every
finished model is copied to /kaggle/working/results at once. Predictions hold ids, gold labels and model JSON, no
record text. AgentRisk is downloaded and converted here (never re-uploaded: no licence).
Inputs: the private code dataset and the private adapter datasets meet6868/agent-risk-adapter (Phase A) and
meet6868/agent-risk-adapter-phase-b.
"""
import glob
import importlib.util
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

WORK = Path("/tmp/repo")
TAGS = ("base", "phase_a", "phase_b")
TRAIN_LOSS = {"phase_a": 0.03732, "phase_b": 0.03356}      # from each adapter's train_stats.json: stops a swapped adapter


def get_code() -> None:
    found = glob.glob("/kaggle/input/**/src/monitor/run.py", recursive=True)
    if found:
        shutil.copytree(Path(found[0]).parents[2], WORK)
        return
    WORK.mkdir(parents=True)
    with tarfile.open(glob.glob("/kaggle/input/**/code.tar.gz", recursive=True)[0]) as tar:
        tar.extractall(WORK)


def find_adapters(base) -> dict[str, Path]:
    """tag -> adapter folder, told apart by the final training loss in train_stats.json."""
    found = {}
    for path in glob.glob("/kaggle/input/**/adapter_config.json", recursive=True):
        if "/epoch_" in path:
            continue
        stats = json.loads((Path(path).parent / "train_stats.json").read_text(encoding="utf-8"))
        tag = next((t for t, loss in TRAIN_LOSS.items() if round(stats["train_loss"], 5) == loss), None)
        if tag is None or tag in found:
            raise SystemExit(f"unexpected adapter {path}: train loss {stats['train_loss']}")
        found[tag] = Path(path).parent
    if set(found) != set(TRAIN_LOSS):
        raise SystemExit(f"expected the Phase A and Phase B adapters, found {found}")
    base.log(f"adapters: {found}")
    return found


def evaluate_model(base, tag: str, adapter: Path | None) -> None:
    runs, tables = WORK / "outputs" / "runs", WORK / "outputs" / "tables"
    title = f"{tag} Qwen3-8B, collected test"
    for name in base.SOURCES:
        base.sh(sys.executable, "-m", "src.monitor.run", "--records", f"inputs/{name}_test.jsonl", "--split", "test",
                "--setting", "never", "--backend", "transformers", "--model", base.MODEL, "--revision",
                base.MODEL_REVISION, *(["--adapter", str(adapter)] if adapter else []),
                "--run-id", f"collected_{tag}_{name}_test", env=base.EVAL_ENV)
        base.sh(sys.executable, "-m", "src.eval.tables", "--run", f"never={runs / f'collected_{tag}_{name}_test'}",
                "--out", str(tables), "--name", f"collected_{tag}_{name}_test", "--title", f"{title}: {name}")
    merged = runs / f"collected_{tag}_test"
    merged.mkdir(parents=True, exist_ok=True)
    with (merged / "predictions.jsonl").open("w", encoding="utf-8") as out:
        for name in base.SOURCES:
            out.write((runs / f"collected_{tag}_{name}_test" / "predictions.jsonl").read_text(encoding="utf-8"))
    base.sh(sys.executable, "-m", "src.eval.tables", "--run", f"never={merged}", "--out", str(tables),
            "--name", f"collected_{tag}_test", "--title", title)
    shutil.copytree(runs, base.OUT / "runs", dirs_exist_ok=True)
    shutil.copytree(tables, base.OUT / "tables", dirs_exist_ok=True)


def main() -> int:
    subprocess.run(["nvidia-smi"], check=False)
    get_code()
    spec = importlib.util.spec_from_file_location("run_finetune", WORK / "kaggle" / "finetune" / "run_finetune.py")
    finetune = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(finetune)
    base = finetune.load_base()
    base.OUT.mkdir(parents=True, exist_ok=True)
    try:
        finetune.setup(base)
        skipped = base.split_inputs("test")
        (base.OUT / "notes.json").write_text(json.dumps({
            "model": base.MODEL, "model_revision": base.MODEL_REVISION, "split": "test",
            "max_tokens": base.MAX_TOKENS, "skipped_long": skipped}, indent=2), encoding="utf-8")
        adapters = find_adapters(base)
        for tag in TAGS:
            evaluate_model(base, tag, adapters.get(tag))
        base.log("all runs finished")
    except Exception:
        import traceback
        base.log("ERROR, traceback follows (results so far are kept)")
        for line in traceback.format_exc().splitlines():
            base.log("  " + line)
        raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
