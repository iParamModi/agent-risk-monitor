"""Strict JSON parsing against the output formats (decisions.md R9.1-R9.3, PLAN 2.6).

Bad output is never repaired (PLAN Step 15.5): anything but one JSON object of the right shape is
invalid. The only thing removed is an empty `<think></think>` block, which the Qwen3 chat template
adds when thinking is off.
"""
import json
import re

from src.monitor.settings import MAX_CHECKS_PER_REQUEST, MAX_REASON_WORDS

DECISIONS = ("ALLOW", "ASK_CONFIRMATION", "BLOCK", "ESCALATE")
RISK_LABELS = ("SAFE", "UNSAFE")
RISK_TYPES = ("DATA_LOSS", "PRIVACY_LEAKAGE", "FINANCIAL_LOSS", "ACCESS_CONTROL", "SECURITY", "OTHER", "NONE")

_EMPTY_THINK = re.compile(r"^\s*<think>\s*</think>")


def _is_str_list(x) -> bool:
    return isinstance(x, list) and all(isinstance(i, str) for i in x)


def valid_decision(obj: dict) -> bool:
    ev = obj.get("evidence")
    return (set(obj) == {"type", "decision", "risk_label", "risk_type", "evidence"}
            and obj["decision"] in DECISIONS and obj["risk_label"] in RISK_LABELS
            and obj["risk_type"] in RISK_TYPES
            and isinstance(ev, dict) and set(ev) == {"facts", "policy_ids"}
            and _is_str_list(ev["facts"]) and _is_str_list(ev["policy_ids"]))


def valid_need_information(obj: dict) -> bool:
    checks = obj.get("checks")
    return (set(obj) == {"type", "reason", "missing_fact", "checks"}
            and isinstance(obj["reason"], str) and len(obj["reason"].split()) <= MAX_REASON_WORDS
            and isinstance(obj["missing_fact"], str)
            and isinstance(checks, list) and 1 <= len(checks) <= MAX_CHECKS_PER_REQUEST
            and all(isinstance(c, dict) and set(c) == {"tool", "args"} and isinstance(c["tool"], str)
                    and isinstance(c["args"], dict) for c in checks))


def valid_risk(obj: dict) -> bool:
    return (set(obj) == {"type", "risk_label", "risk_type"}
            and obj["risk_label"] in RISK_LABELS and obj["risk_type"] in RISK_TYPES)


_VALIDATORS = {"DECISION": valid_decision, "NEED_INFORMATION": valid_need_information, "RISK": valid_risk}


def parse_output(text: str | None, allowed: tuple[str, ...]) -> dict | None:
    """The parsed object if `text` is exactly one JSON object whose `type` is in `allowed` and whose
    shape is valid for that type; otherwise None (invalid, R9.6)."""
    if not text:
        return None
    text = _EMPTY_THINK.sub("", text, count=1).strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict) or obj.get("type") not in allowed:
        return None
    return obj if _VALIDATORS[obj["type"]](obj) else None
