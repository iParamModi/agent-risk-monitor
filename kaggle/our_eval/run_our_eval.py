"""Kaggle job: our records in all 4 settings (never / always / selective / oracle), for base Qwen3-8B and/or the
Phase B adapter, each with two policy conditions (decisions.md 2026-10-28):
  gold       the gold policies + 2 retrieved look-alikes, as in training: checking and deciding alone
  retrieval  the top 3 retrieved policies: the full system
Splits: val, the locked in-domain test (R15.2: the 30 Oct submission reports validation and test) and the locked
OOD test (PLAN Step 20; kaggle/ood_*/). In-domain: phase 1 records only, as in training (configs/tool_phases.yaml):
the 4 phase-2 create_event test records are left out. OOD: all 112, with the OOD policy store and check tools (set by
record["set"] in src/monitor/case_inputs.py). Nothing here trains or tunes: the test records are only run and scored.

Each model is loaded once for its runs (src.monitor.run.run_records). Per run: predictions.jsonl, traces.jsonl
(every pass and gateway call, read with scripts/show_traces.py), invalid_outputs.jsonl; per model, condition and
split one src.eval.tables report over the 4 settings. Every finished run is copied to /kaggle/working/results at
once, so a job that hits the time limit keeps what it finished.

One job per model (kaggle/our_eval_final_base/, kaggle/our_eval_final_phase_b/) call main(tags=...); running this
file alone does both models on val (the first val-only run). plan= picks the system version, policy condition and
settings per entry (src/monitor/case_inputs.py VERSIONS; kaggle/v2_*/); v1 run ids keep their names, other versions
get the version after the model tag (ours_<model>_<version>_<policies>_<setting>_<split>). Split "train_two_check" =
the train records that need two checks: a check of the loop's mechanics on records the model was trained on.
Inputs: the private code dataset and the private Phase B adapter dataset (meet6868/agent-risk-adapter-phase-b).
"""
import gc
import glob
import importlib.util
import shutil
import sys
import time
from pathlib import Path

WORK = Path("/tmp/repo")
SETTINGS = ("never", "always", "selective", "oracle")
POLICY_MODES = ("gold", "retrieval")
RECORD_FILES = {"val": "data/records/val.jsonl", "test": "data/records/test.jsonl", "ood": "data/records/ood_test.jsonl",
                "train_two_check": "data/records/train.jsonl"}
DEFAULT_PLAN = tuple({"version": "v1", "mode": m, "settings": SETTINGS} for m in POLICY_MODES)


def run_name(tag: str, version: str, mode: str, setting: str, split: str) -> str:
    return f"ours_{tag}_{mode}_{setting}_{split}" if version == "v1" else f"ours_{tag}_{version}_{mode}_{setting}_{split}"


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


def load_records(base, split: str) -> list[dict]:
    """The split's phase 1 decide_action records, the same filter as the training file (build_sft.phase1).
    OOD: every record (its new tools are in no phase, so that filter does not apply)."""
    from src.common.io import read_jsonl
    from src.training.build_sft import phase1
    if split == "ood":
        kept = list(read_jsonl(WORK / RECORD_FILES[split]))
        base.log(f"ood: {len(kept)} records")
        return kept
    if split == "train_two_check":
        kept = [r for r in phase1(list(read_jsonl(WORK / RECORD_FILES[split])), "train")
                if len(r["gold"]["required_checks"] or []) >= 2]
        base.log(f"train_two_check: {len(kept)} records")
        return kept
    records = [r for r in read_jsonl(WORK / RECORD_FILES[split]) if r["split"] == split]
    kept = phase1(records, split)
    base.log(f"{split}: {len(kept)} phase 1 records ({len(records) - len(kept)} phase 2 left out)")
    return kept


def save(base, sub: str) -> None:
    """Copy outputs/<sub> to the job's output folder now (kept even if the job is stopped later)."""
    src = WORK / "outputs" / sub
    if src.exists():
        shutil.copytree(src, base.OUT / sub, dirs_exist_ok=True)


def evaluate_model(base, tag: str, adapter: str | None, splits: tuple[str, ...], plan=DEFAULT_PLAN) -> None:
    """The plan's runs per split with one model load (default: v1, 2 policy conditions x 4 settings), then one report
    per version, condition and split that has all 4 settings."""
    import torch
    from src.monitor.case_inputs import CaseInputs
    from src.monitor.models import TransformersModel
    from src.monitor.prompt_builder import template_names
    from src.monitor.run import RUNS_DIR, Recording, run_records

    base.log(f"{tag}: loading the model ({'adapter ' + adapter if adapter else 'no adapter'})")
    model = Recording(TransformersModel(base.MODEL, base.MODEL_REVISION, adapter))
    embedder = None
    for split in splits:
        records = load_records(base, split)
        for entry in (plan[split] if isinstance(plan, dict) else plan):     # one plan, or {split: plan}
            version, mode = entry["version"], entry["mode"]
            inputs = CaseInputs(embedder=embedder, policy_mode=mode, version=version)
            for setting in entry["settings"]:
                run_id = run_name(tag, version, mode, setting, split)
                base.log(f"start: {run_id} ({len(records)} records)")
                t0 = time.perf_counter()
                rows = run_records(records, setting, model, inputs, run_id, RUNS_DIR / run_id, config={
                    "run_id": run_id, "setting": setting, "model": model.name, "backend": "transformers",
                    "revision": base.MODEL_REVISION, "adapter": adapter, "split": split,
                    "records": [RECORD_FILES[split]], "prompts": template_names(), "policies": mode,
                    "version": version})
                right = sum(bool(r["output"]) and r["output"]["decision"] == r["gold"]["decision"] for r in rows)
                errors = sum(c["error"] is not None for r in rows for c in r["calls"])
                base.log(f"done: {run_id} | decision right {right}/{len(rows)} | invalid "
                         f"{sum(r['output'] is None for r in rows)} | gateway calls {sum(len(r['calls']) for r in rows)} "
                         f"({errors} errors) | {(time.perf_counter() - t0) / 60:.1f} min")
                save(base, "runs")
                embedder = inputs.embedder                  # load the embedding model once
            if tuple(entry["settings"]) != SETTINGS:
                continue
            runs = [f"--run={s}={RUNS_DIR / run_name(tag, version, mode, s, split)}" for s in SETTINGS]
            name = run_name(tag, version, mode, "x", split).replace("_x_", "_")
            base.sh(sys.executable, "-m", "src.eval.tables", *runs, "--out", str(WORK / "outputs" / "tables"),
                    "--name", name, "--title", f"Our {split} records, {tag}, {version}, policies: {mode}")
            save(base, "tables")
    del model
    gc.collect()
    torch.cuda.empty_cache()


def main(tags: tuple[str, ...] = ("base", "phase_b"), splits: tuple[str, ...] = ("val",), plan=DEFAULT_PLAN) -> int:
    import subprocess
    subprocess.run(["nvidia-smi"], check=False)
    here = Path(__file__).resolve().parents[1] / "finetune" / "run_finetune.py"     # loaded from the code dataset
    path = here if here.exists() else Path(glob.glob("/kaggle/input/**/kaggle/finetune/run_finetune.py",
                                                     recursive=True)[0])          # run as a kernel's own file
    finetune = load_module("run_finetune", path)
    finetune.get_code()                             # the code dataset -> /tmp/repo (unpacked or code.tar.gz)
    sys.path.insert(0, str(WORK))
    base = finetune.load_base()
    base.OUT.mkdir(parents=True, exist_ok=True)
    try:
        base.sh(sys.executable, "-m", "pip", "install", "-q", *base.PIP, *finetune.PIP_PHASE_B)
        base.sh(sys.executable, "-m", "pip", "uninstall", "-y", "-q", "torchao")
        log_environment(base)
        base.log(f"models {tags}, splits {splits}, plan {plan}")
        for tag in tags:
            evaluate_model(base, tag, find_adapter(base) if tag == "phase_b" else None, splits, plan)
        base.log("all runs finished")
    except Exception:
        import traceback
        base.log("ERROR, traceback follows (results so far are kept)")
        for line in traceback.format_exc().splitlines():
            base.log("  " + line)
        raise
    finally:
        save(base, "runs")
        save(base, "tables")
    return 0


if __name__ == "__main__":
    sys.exit(main())
