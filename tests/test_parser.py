"""Tests for strict JSON parsing."""
import json

from src.monitor.parser import parse_output

DECISION = {"type": "DECISION", "decision": "BLOCK", "risk_label": "UNSAFE", "risk_type": "PRIVACY_LEAKAGE",
            "evidence": {"facts": ["a.xlsx sharing = public"], "policy_ids": ["P_PRIV_07"]}}
NEED = {"type": "NEED_INFORMATION", "reason": "The file was moved.", "missing_fact": "sharing of a.xlsx",
        "checks": [{"tool": "check_file_sharing", "args": {"file": "a.xlsx"}}]}
RISK = {"type": "RISK", "risk_label": "SAFE", "risk_type": "NONE"}
BOTH = ("DECISION", "NEED_INFORMATION")


def test_valid_objects_parse():
    assert parse_output(json.dumps(DECISION), BOTH) == DECISION
    assert parse_output(json.dumps(NEED), BOTH) == NEED
    assert parse_output(json.dumps(RISK), ("RISK",)) == RISK


def test_empty_think_block_is_removed_only_when_empty():
    assert parse_output("<think>\n\n</think>\n\n" + json.dumps(RISK), ("RISK",)) == RISK
    assert parse_output("<think>hmm</think>" + json.dumps(RISK), ("RISK",)) is None


def test_no_repair():
    for bad in ["", None, "```json\n" + json.dumps(RISK) + "\n```", "Answer: " + json.dumps(RISK),
                json.dumps(RISK) + " done", json.dumps(RISK)[:-1], "[1]"]:
        assert parse_output(bad, ("RISK",)) is None


def test_type_must_be_allowed():
    assert parse_output(json.dumps(NEED), ("DECISION",)) is None
    assert parse_output(json.dumps(DECISION), ("RISK",)) is None


def test_bad_values_and_extra_or_missing_keys():
    assert parse_output(json.dumps({**DECISION, "decision": "DENY"}), BOTH) is None
    assert parse_output(json.dumps({**DECISION, "risk_type": "PRIVACY"}), BOTH) is None
    assert parse_output(json.dumps({**DECISION, "note": "x"}), BOTH) is None
    assert parse_output(json.dumps({k: v for k, v in DECISION.items() if k != "evidence"}), BOTH) is None
    assert parse_output(json.dumps({**DECISION, "evidence": {"facts": "x", "policy_ids": []}}), BOTH) is None


def test_need_information_limits():
    three = [{"tool": "check_a", "args": {}}] * 3
    assert parse_output(json.dumps({**NEED, "checks": three}), BOTH) is None
    assert parse_output(json.dumps({**NEED, "checks": []}), BOTH) is None
    assert parse_output(json.dumps({**NEED, "reason": "word " * 31}), BOTH) is None
    assert parse_output(json.dumps({**NEED, "reason": "word " * 30}), BOTH) is not None
    assert parse_output(json.dumps({**NEED, "checks": [{"tool": "check_a", "args": "x"}]}), BOTH) is None
