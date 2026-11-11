"""Kaggle job: the val check of system v2 (decisions.md 2026-11-11), final Phase B adapter only, before any v2 run
on test or OOD. Val: v2 with retrieved policies in the 4 settings, v2_retrieval (retrieval change only) selective,
v2 selective with correct policies. Train records that need two checks (the model was trained on them, so this
checks the loop's mechanics, not generalisation): v1 and v2 selective with correct policies. The decision rule
is in decisions.md; v1 val numbers come from the 11 Nov final run (kaggle/our_eval_final_phase_b/)."""
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
ALL = job.SETTINGS
PLAN = {"val": ({"version": "v2", "mode": "retrieval", "settings": ALL},
                {"version": "v2_retrieval", "mode": "retrieval", "settings": ("selective",)},
                {"version": "v2", "mode": "gold", "settings": ("selective",)}),
        "train_two_check": ({"version": "v1", "mode": "gold", "settings": ("selective",)},
                            {"version": "v2", "mode": "gold", "settings": ("selective",)})}
sys.exit(job.main(tags=("phase_b",), splits=("val", "train_two_check"), plan=PLAN))
