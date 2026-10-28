"""Kaggle job: our val records in all 4 settings (never / always / selective / oracle), base Qwen3-8B and the Phase B
adapter, each with two policy conditions (decisions.md 2026-10-28):
  gold       the gold policies + 2 retrieved look-alikes, as in training: checking and deciding alone
  retrieval  the top 3 retrieved policies: the full system
Each model is loaded once for its 8 runs (src.monitor.run.run_records). Per run: predictions.jsonl, traces.jsonl
(every pass and gateway call, read with scripts/show_traces.py), invalid_outputs.jsonl; per model and condition one
src.eval.tables report over the 4 settings (hypothesis selective vs always, savings, check metrics). Val only: the
test and OOD files stay locked. Results (our records only, no external text) go to /kaggle/working/results.
Inputs: the private code dataset and the private Phase B adapter dataset (meet6868/agent-risk-adapter-phase-b).
"""
import gc
import glob
import importlib.util
import shutil
import sys
from pathlib import Path

WORK = Path("/tmp/repo")
SETTINGS = ("never", "always", "selective", "oracle")
POLICY_MODES = ("gold", "retrieval")
RECORDS = "data/records/val.jsonl"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def log_environment(base) -> None:
    import importlib.metadata as md
    import torch
    commit = glob.glob("/kaggle/input/**/code_commit.txt", recursive=True)
    base.log("code: " + (Path(commit[0]).read_text(encoding="utf-8").strip() if commit else "commit unknown"))
    base.log(", ".join(f"{p} {md.version(p)}" for p in ("torch", "transformers", "peft", "sentence-transformers")))
    for i in range(torch.cuda.device_count()):
        free, total = torch.cuda.mem_get_info(i)
        base.log(f"GPU {i}: {torch.cuda.get_device_name(i)}, {free / 2**30:.1f} of {total / 2**30:.1f} GiB free")


def find_adapter(base) -> str:
    found = [p for p in glob.glob("/kaggle/input/**/adapter_config.json", recursive=True) if "/epoch_" not in p]
    if len(found) != 1:
        base.sh("find", "/kaggle/input", "-maxdepth", "4")
        raise SystemExit(f"expected one Phase B adapter in /kaggle/input, found {found}")
    return str(Path(found[0]).parent)


def evaluate_model(base, tag: str, adapter: str | None) -> None:
    """8 runs (2 policy conditions x 4 settings) with one model load, then one report per condition."""
    import torch
    sys.path.insert(0, str(WORK))
    from src.common.io import read_jsonl
    from src.monitor.case_inputs import CaseInputs
    from src.monitor.models import TransformersModel
    from src.monitor.prompt_builder import template_names
    from src.monitor.run import RUNS_DIR, Recording, run_records

    records = [r for r in read_jsonl(WORK / RECORDS) if r["split"] == "val"]
    base.log(f"{tag}: loading the model ({'adapter ' + adapter if adapter else 'no adapter'}), {len(records)} val records")
    model = Recording(TransformersModel(base.MODEL, base.MODEL_REVISION, adapter))
    embedder = None
    for mode in POLICY_MODES:
        inputs = CaseInputs(embedder=embedder, policy_mode=mode)
        for setting in SETTINGS:
            run_id = f"ours_{tag}_{mode}_{setting}"
            base.log(f"start: {run_id}")
            rows = run_records(records, setting, model, inputs, run_id, RUNS_DIR / run_id, config={
                "run_id": run_id, "setting": setting, "model": model.name, "backend": "transformers",
                "revision": base.MODEL_REVISION, "adapter": adapter, "split": "val", "records": [RECORDS],
                "prompts": template_names(), "policies": mode})
            right = sum(bool(r["output"]) and r["output"]["decision"] == r["gold"]["decision"] for r in rows)
            base.log(f"done: {run_id} | decision right {right}/{len(rows)} | invalid "
                     f"{sum(r['output'] is None for r in rows)} | gateway calls {sum(len(r['calls']) for r in rows)}")
        embedder = inputs.embedder                      # load the embedding model once
        runs = [f"--run={s}={RUNS_DIR / f'ours_{tag}_{mode}_{s}'}" for s in SETTINGS]
        base.sh(sys.executable, "-m", "src.eval.tables", *runs, "--out", str(WORK / "outputs" / "tables"),
                "--name", f"ours_{tag}_{mode}_val", "--title", f"Our val records, {tag}, policies: {mode}")
    del model
    gc.collect()
    torch.cuda.empty_cache()


def main() -> int:
    import subprocess
    subprocess.run(["nvidia-smi"], check=False)
    found = glob.glob("/kaggle/input/**/src/monitor/run.py", recursive=True)
    shutil.copytree(Path(found[0]).parents[2], WORK)
    finetune = load_module("run_finetune", WORK / "kaggle" / "finetune" / "run_finetune.py")
    base = finetune.load_base()
    try:
        base.sh(sys.executable, "-m", "pip", "install", "-q", *base.PIP, *finetune.PIP_PHASE_B)
        base.sh(sys.executable, "-m", "pip", "uninstall", "-y", "-q", "torchao")
        log_environment(base)
        adapter = find_adapter(base)
        for tag, path in (("base", None), ("phase_b", adapter)):
            evaluate_model(base, tag, path)
    except Exception:
        import traceback
        base.log("ERROR, traceback follows (results so far are kept)")
        for line in traceback.format_exc().splitlines():
            base.log("  " + line)
        raise
    finally:
        out = base.OUT
        out.mkdir(parents=True, exist_ok=True)
        for sub in ("runs", "tables"):
            if (WORK / "outputs" / sub).exists():
                shutil.copytree(WORK / "outputs" / sub, out / sub, dirs_exist_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
