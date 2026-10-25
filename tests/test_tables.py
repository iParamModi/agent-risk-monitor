"""Report builder: every section is filled, runs must match, CLI writes both files."""
import json

import pytest

from src.common.io import write_jsonl
from src.eval import tables


def case(rid, seed, gold, pred, calls=0, case_type="T3", side=None, subtype=None, needed=False):
    risky = lambda d: d != "ALLOW"  # noqa: E731
    return {"record_id": rid, "seed_id": seed, "domain": "FILE", "case_type": case_type, "subtype": subtype,
            "pair_side": side, "task": "decide_action",
            "gold": {"decision": gold, "risk_label": "UNSAFE" if risky(gold) else "SAFE",
                     "risk_type": "DATA_LOSS" if risky(gold) else "NONE", "check_needed": needed,
                     "required_checks": [{"tool": "check_file_sharing", "args": {"file": "f"}}] if needed else None},
            "output": {"type": "DECISION", "decision": pred, "risk_label": "UNSAFE" if risky(pred) else "SAFE",
                       "risk_type": "DATA_LOSS" if risky(pred) else "NONE"},
            "calls": [{"tool": "check_file_sharing", "args": {"file": "f"}, "error": None}] * calls,
            "passes": 1, "tokens_in": 100, "tokens_out": 10, "time_s": 1.0}


def runs():
    base = [("r1", "S1", "ALLOW", "T1", "A", None, True), ("r2", "S1", "BLOCK", "T1", "B", None, True),
            ("r3", "S2", "BLOCK", "T2", None, "c", True), ("r4", "S3", "ALLOW", "T3", None, None, False),
            ("r5", "S4", "BLOCK", "T4", None, None, False)]
    always = [case(r, s, g, g, 2, ct, side, st, n) for r, s, g, ct, side, st, n in base]
    selective = [case(r, s, g, g if r != "r3" else "ALLOW", 1 if n and r != "r3" else 0, ct, side, st, n)
                 for r, s, g, ct, side, st, n in base]
    return {"always": always, "selective": selective}


def test_build_report_fills_every_part():
    rep = tables.build_report(runs(), n_resamples=50)
    assert set(rep["settings"]) == {"always", "selective"}
    assert rep["saving"]["selective"] == pytest.approx(1 - 2 / 10)
    assert rep["oracle_saving"] == pytest.approx(1 - 3 / 10)
    assert rep["hypothesis"]["value"] == pytest.approx(1 / 3)       # r3 let through: 1 of 3 risky
    assert not rep["hypothesis"]["passes"]
    assert rep["selective_vs_always"]["tests"]["correct"]["by_case"]["only_b_right"] == 1
    md = tables.to_markdown(rep)
    for section in ("## Hypothesis", "## Main metrics", "## Selective vs always", "## Checks",
                    "## Decision F1 per class", "## Risk label and risk type", "## Accuracy per case type",
                    "## T2 accuracy per subtype", "## Accuracy per domain", "## Cost and tool use"):
        assert section in md
    assert "FAILS" in md


def test_report_without_selective_has_no_hypothesis():
    rep = tables.build_report({"always": runs()["always"]}, n_resamples=20)
    assert "hypothesis" not in rep and "## Hypothesis" not in tables.to_markdown(rep)


def test_runs_must_cover_the_same_records():
    r = runs()
    r["selective"] = r["selective"][:-1]
    with pytest.raises(ValueError):
        tables.build_report(r, n_resamples=10)


def test_cli_writes_markdown_and_json(tmp_path):
    for name, cases in runs().items():
        write_jsonl(tmp_path / name / "predictions.jsonl", cases)
    out = tmp_path / "report"
    assert tables.main(["--run", f"always={tmp_path / 'always'}", "--run", f"selective={tmp_path / 'selective'}",
                        "--out", str(out), "--resamples", "20"]) == 0
    assert "## Main metrics" in (out / "main.md").read_text(encoding="utf-8")
    assert json.loads((out / "main.json").read_text(encoding="utf-8"))["n_resamples"] == 20


def test_formatting_helpers():
    assert tables.pct(None) == "–" and tables.pct(0.1234) == "12.3"
    assert tables.p_value(0.0004) == "< 0.001" and tables.p_value(0.25) == "0.250"
