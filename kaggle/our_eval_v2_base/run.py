"""Kaggle job: the final run of system v2 (decisions.md 2026-11-11) for base Qwen3-8B on val, the locked test
and OOD. v2 changes retrieval (every setting with retrieved policies) and the selective loop; with correct policies
only selective changes, so never / always / oracle with correct policies are the v1 runs of kaggle/our_eval_final_base/
and kaggle/ood_base/ (scripts/final_results.py --version v2 puts them together). Started only after the val check
passed the decision rule."""
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
PLAN = ({"version": "v2", "mode": "retrieval", "settings": job.SETTINGS},
        {"version": "v2", "mode": "gold", "settings": ("selective",)})
sys.exit(job.main(tags=("base",), splits=("val", "test", "ood"), plan=PLAN))
