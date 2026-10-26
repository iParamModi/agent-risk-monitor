"""scripts/make_agentrisk_recheck.py (who labels what, which options) and the viewer's --check."""
import csv
import importlib.util
from collections import Counter


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, f"scripts/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mk = load_script("make_agentrisk_recheck")


def test_needs_person_and_options():
    assert mk.needs_person(["Privacy / Confidentiality", "Security / System Integrity"]) == \
        ("two domains", ["SECURITY", "PRIVACY_LEAKAGE"])
    assert mk.needs_person(["Physical / Health", "Security / System Integrity"]) == ("two domains", ["SECURITY", "OTHER"])
    assert mk.needs_person(["Operational / Service"]) == ("mixed domain", ["DATA_LOSS", "SECURITY", "OTHER"])
    assert mk.needs_person(["Operational / Service", "Financial / Assets"]) == \
        ("mixed domain", ["FINANCIAL_LOSS", "DATA_LOSS", "SECURITY", "OTHER"])
    assert mk.needs_person(["Financial / Assets"]) is None                      # map decides
    assert mk.needs_person(["Legal / Compliance", "Environmental"]) is None     # both OTHER


def item(i, split="train", reason="two domains", pair="A + B"):
    return {"record_id": f"AR-{i:03d}", "split": split, "reason": reason, "options": ["X", "Y"], "group": (split, reason, pair)}


def test_assign_is_even_overall_and_per_group():
    items = [item(i, split="test" if i % 5 == 0 else "train", pair="A + B" if i % 3 else "C + D") for i in range(1, 103)]
    mk.assign(items)
    load = Counter(it["assigned_to"] for it in items)
    assert set(load) == set(mk.LABELLERS) and max(load.values()) - min(load.values()) <= 1
    test_load = Counter(it["assigned_to"] for it in items if it["split"] == "test")
    assert max(test_load.values()) - min(test_load.values()) <= 1


def test_assign_is_repeatable():
    a, b = [item(i) for i in range(1, 30)], [item(i) for i in range(1, 30)]
    mk.assign(a)
    mk.assign(b)
    assert [x["assigned_to"] for x in a] == [x["assigned_to"] for x in b]


def test_viewer_check_rejects_values_outside_the_options(tmp_path, monkeypatch, capsys):
    viewer = load_script("show_agentrisk_recheck")
    sheet = tmp_path / "s.csv"
    with open(sheet, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(mk.COLUMNS)
        w.writerow(["AR-001", "Meet", "train", "two domains", "SECURITY | PRIVACY_LEAKAGE", "SECURITY", ""])
        w.writerow(["AR-002", "Meet", "train", "two domains", "SECURITY | PRIVACY_LEAKAGE", "CONFUSED", "torn"])
        w.writerow(["AR-003", "Param", "val", "two domains", "SECURITY | OTHER", "", ""])
    monkeypatch.setattr(viewer, "SHEET", sheet)
    assert viewer.check() == 0
    with open(sheet, "a", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(["AR-004", "Param", "val", "two domains", "SECURITY | OTHER", "DATA_LOSS", ""])
    assert viewer.check() == 1
    assert "NOT AN OPTION: AR-004 (Param): 'DATA_LOSS'" in capsys.readouterr().out


imp = load_script("import_agentrisk_labels")


def sheet_rows():
    return [{"record_id": "AR-001", "assigned_to": "Meet", "split": "train", "reason": "two domains",
             "options": "SECURITY | OTHER", "recheck_type": "", "recheck_note": ""},
            {"record_id": "AR-002", "assigned_to": "Param", "split": "val", "reason": "two domains",
             "options": "SECURITY | OTHER", "recheck_type": "", "recheck_note": ""}]


def test_import_reads_done_field():
    text = ("[1/2] AR-001   (split: train, two domains)   for: Meet   done: SECURITY\nother\n"
            "[2/2] AR-009   (split: val, x)   done: -\n")
    assert imp.read_labels(text) == {"AR-001": "SECURITY"}


def test_import_fills_only_own_valid_rows():
    rows = sheet_rows()
    assert imp.apply(rows, "Meet", {"AR-001": "OTHER", "AR-002": "SECURITY"}) == ([], 1)    # AR-002 is Param's: skipped
    assert rows[0]["recheck_type"] == "OTHER" and rows[1]["recheck_type"] == ""
    rows = sheet_rows()
    problems, _ = imp.apply(rows, "Meet", {"AR-001": "DATA_LOSS", "AR-777": "OTHER"})
    assert len(problems) == 2
