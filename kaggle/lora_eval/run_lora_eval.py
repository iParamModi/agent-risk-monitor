"""Kaggle job: score a saved QLoRA adapter on the external val records, without training again.

The adapter comes from the PRIVATE Kaggle dataset meet6868/agent-risk-adapter (the adapter folder that
kaggle/finetune saved; uploaded by hand because Kaggle does not offer a failed run's output as input). Same steps, code and float16 precision as the evaluation part of kaggle/finetune (its setup() and
evaluate()), so the result compares with kaggle/base_eval. Used on 2026-10-27: fine-tune v4 trained and saved the
adapter, then its evaluation stopped on a torchao version clash (fixed in setup()).
"""
import glob
import importlib.util
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

WORK = Path("/tmp/repo")


def get_code() -> None:
    found = glob.glob("/kaggle/input/**/src/monitor/run.py", recursive=True)
    if found:
        shutil.copytree(Path(found[0]).parents[2], WORK)
        return
    WORK.mkdir(parents=True)
    with tarfile.open(glob.glob("/kaggle/input/**/code.tar.gz", recursive=True)[0]) as tar:
        tar.extractall(WORK)


def main() -> int:
    subprocess.run(["nvidia-smi"], check=False)
    get_code()
    spec = importlib.util.spec_from_file_location("run_finetune", WORK / "kaggle" / "finetune" / "run_finetune.py")
    finetune = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(finetune)
    base = finetune.load_base()
    found = glob.glob("/kaggle/input/**/adapter_config.json", recursive=True)
    if len(found) != 1:
        subprocess.run(["find", "/kaggle/input", "-maxdepth", "4"], check=False)
        raise SystemExit(f"expected one adapter in /kaggle/input, found {found}")
    adapter = Path(found[0]).parent
    base.log(f"adapter: {adapter}")
    finetune.setup(base)
    finetune.evaluate(base, adapter)
    return 0


if __name__ == "__main__":
    sys.exit(main())
