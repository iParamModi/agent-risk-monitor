"""scripts/make_untyped_recheck.py: reading the labels typed after 'done:'."""
import importlib.util

spec = importlib.util.spec_from_file_location("make_untyped_recheck", "scripts/make_untyped_recheck.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_read_labels_takes_only_filled_headers():
    text = ("[1/3] RJ-dh_app-1002   (R-Judge, split: train)   for: Meet   done: FINANCIAL_LOSS\n"
            "--- user ---\nsome text done: SECURITY\n"
            "[2/3] ATB-12   (ATBench, split: train)   for: Meet   done: -\n"
            "[3/3] ATB-40   (ATBench, split: train)   for: Meet   done: CONFUSED  \n")
    assert mod.read_labels(text) == {"RJ-dh_app-1002": "FINANCIAL_LOSS", "ATB-40": "CONFUSED"}
