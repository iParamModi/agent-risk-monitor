"""Kaggle job: the Phase B adapter on the locked OOD test (112 records, PLAN Step 20), 4 settings x 2 policy
conditions (kaggle/our_eval/run_our_eval.py, from the code dataset). Results in /kaggle/working/results."""
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
sys.exit(job.main(tags=("phase_b",), splits=("ood",)))
