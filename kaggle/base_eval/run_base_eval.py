"""Kaggle job: base Qwen3-8B (float16, GPU T4 x2) on the external val records, scored by src.eval.

Runs as a private Kaggle script (kaggle/README.md). Steps:
1. code from the private dataset meet6868/agent-risk-code (git archive of the repo: no .env, no AgentRisk)
2. AgentRisk downloaded from Hugging Face at the pinned revision and converted here (never re-uploaded: no licence)
3. token counts, then val records up to MAX_TOKENS (the very long ATBench ones are left out, listed in notes.json)
4. one monitor run per source (judge_trajectory = one pass, no checks), merged, scored with src.eval.tables
Only results go to /kaggle/working/results (predictions hold ids, gold labels and model JSON, no record text).
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

MODEL = "Qwen/Qwen3-8B"
MODEL_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"      # same as src/common/tokens.py
AGENTRISK_REPO = "AgentRisk/agentrisk-data-2027"
AGENTRISK_REVISION = "bc7cbf702846e53ecbb31abcdb387ae4ec9f9392"  # same as scripts/download_external.sh
SOURCES = ("r_judge", "atbench", "agentrisk")
MAX_TOKENS = 7300
RUN_TAG = "base_qwen3_8b_fp16"
# shared with kaggle/finetune (same libraries for the base and the fine-tuned run); code works with transformers 4.56+ and 5.x
PIP = ["transformers>=4.56", "accelerate", "peft", "bitsandbytes", "jsonschema", "pyyaml", "python-dotenv", "tokenizers"]
WORK = Path("/tmp/repo")
OUT = Path("/kaggle/working/results")
# eval runs (also kaggle/finetune): less memory fragmentation with prompts of very different lengths
EVAL_ENV = {**os.environ, "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"}


PROGRESS = Path("/kaggle/working/progress.log")     # kept in the job output even if the job fails


def log(msg: str) -> None:
    from datetime import datetime, timezone
    line = f"[{datetime.now(timezone.utc):%H:%M:%S} UTC] {msg}"
    print(line, flush=True)
    with PROGRESS.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def sh(*cmd: str, env: dict | None = None) -> None:
    """Runs a step; its output lines starting with '[' (progress) also go to progress.log."""
    log("start: " + " ".join(cmd[2:] if cmd[:2] == (sys.executable, "-m") else cmd))
    proc = subprocess.Popen(cmd, cwd=WORK, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in proc.stdout:
        print(line, end="", flush=True)
        for tag in ("[run]", "[train]"):        # may follow a progress bar's \r on the same line
            if tag in line:
                log(line[line.index(tag):].strip())
    if proc.wait():
        log(f"FAILED (exit {proc.returncode})")
        raise subprocess.CalledProcessError(proc.returncode, cmd)
    log("done")


def get_code() -> None:
    found = glob.glob("/kaggle/input/**/src/monitor/run.py", recursive=True)
    if found:
        shutil.copytree(Path(found[0]).parents[2], WORK)
        return
    WORK.mkdir(parents=True)
    with tarfile.open(glob.glob("/kaggle/input/**/code.tar.gz", recursive=True)[0]) as tar:
        tar.extractall(WORK)


def get_agentrisk() -> None:
    from huggingface_hub import hf_hub_download
    for f in ("data/train.jsonl", "data/dev.jsonl", "metadata/split_manifest.jsonl"):
        hf_hub_download(AGENTRISK_REPO, f, repo_type="dataset", revision=AGENTRISK_REVISION,
                        local_dir=WORK / "data" / "raw" / "agentrisk")


def split_inputs(split: str = "val") -> list[dict]:
    (WORK / "inputs").mkdir(exist_ok=True)
    skipped = []
    for name in SOURCES:
        keep = []
        for line in (WORK / "data" / "external" / f"{name}.jsonl").open(encoding="utf-8"):
            r = json.loads(line)
            if r["split"] != split:
                continue
            if r["meta"]["n_tokens"] > MAX_TOKENS:
                skipped.append({"record_id": r["record_id"], "tokens": r["meta"]["n_tokens"], "label": r["gold"]["risk_label"]})
                continue
            keep.append(line)
        (WORK / "inputs" / f"{name}_{split}.jsonl").write_text("".join(keep), encoding="utf-8")
        print(f"{name}: {len(keep)} {split} records", flush=True)
    return skipped


def main() -> int:
    subprocess.run(["nvidia-smi"], check=False)
    get_code()
    sh(sys.executable, "-m", "pip", "install", "-q", *PIP)
    get_agentrisk()
    sh(sys.executable, "-m", "src.external.agentrisk")
    sh(sys.executable, "-m", "src.external.count_tokens")
    skipped = split_inputs()

    runs = WORK / "outputs" / "runs"
    for name in SOURCES:
        sh(sys.executable, "-m", "src.monitor.run", "--records", f"inputs/{name}_val.jsonl", "--split", "val",
           "--setting", "never", "--backend", "transformers", "--model", MODEL, "--revision", MODEL_REVISION,
           "--run-id", f"{RUN_TAG}_{name}", env=EVAL_ENV)
    merged = runs / f"{RUN_TAG}_val"
    merged.mkdir(parents=True, exist_ok=True)
    with (merged / "predictions.jsonl").open("w", encoding="utf-8") as out:
        for name in SOURCES:
            out.write((runs / f"{RUN_TAG}_{name}" / "predictions.jsonl").read_text(encoding="utf-8"))
    tables = WORK / "outputs" / "tables"
    sh(sys.executable, "-m", "src.eval.tables", "--run", f"never={merged}", "--out", str(tables),
       "--name", f"{RUN_TAG}_val", "--title", "Base Qwen3-8B (fp16), external val")
    for name in SOURCES:
        sh(sys.executable, "-m", "src.eval.tables", "--run", f"never={runs / f'{RUN_TAG}_{name}'}", "--out", str(tables),
           "--name", f"{RUN_TAG}_val_{name}", "--title", f"Base Qwen3-8B (fp16), {name} val")

    import torch
    import transformers
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copytree(runs, OUT / "runs", dirs_exist_ok=True)
    shutil.copytree(tables, OUT / "tables", dirs_exist_ok=True)
    (OUT / "notes.json").write_text(json.dumps({
        "model": MODEL, "model_revision": MODEL_REVISION, "dtype": "float16", "agentrisk_revision": AGENTRISK_REVISION,
        "max_tokens": MAX_TOKENS, "skipped_long": skipped, "transformers": transformers.__version__,
        "torch": torch.__version__, "peft": __import__("peft").__version__, "gpus": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
    }, indent=2), encoding="utf-8")
    print("done:", sorted(p.name for p in (OUT / "tables").iterdir()), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
