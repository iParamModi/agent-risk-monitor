"""Kaggle job: the val check of the v3 candidates (decisions.md 2026-11-12), final Phase B adapter, selective only
(v3 changes nothing else), retrieved and correct policies, before any v3 run on test or OOD. The v2 numbers it is
compared with come from kaggle/v2_val_check/."""
import glob
import importlib.util
import sys
import tarfile
from pathlib import Path

found = glob.glob("/kaggle/input/**/kaggle/our_eval/run_our_eval.py", recursive=True)
if not found:                                   # the code dataset was not unpacked: unpack it once
    with tarfile.open(glob.glob("/kaggle/input/**/code.tar.gz", recursive=True)[0]) as tar:
        tar.extractall("/tmp/code_src")
    found = ["/tmp/code_src/kaggle/our_eval/run_our_eval.py"]
spec = importlib.util.spec_from_file_location("run_our_eval", Path(found[0]))
job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)
PLAN = tuple({"version": v, "mode": mode, "settings": ("selective",)}
             for v in ("v3", "v3_ask") for mode in ("retrieval", "gold"))
sys.exit(job.main(tags=("phase_b",), splits=("val",), plan=PLAN))
