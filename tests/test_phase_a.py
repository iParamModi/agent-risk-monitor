"""src/external/phase_a.py on synthetic records."""
import random
from collections import Counter

from src.external.phase_a import downsample, pick_unsafe


def rec(i, label, rtype=None, cause=None, reply=False, source="agentrisk"):
    return {"record_id": f"X-{i:03d}", "source": source, "gold": {"risk_label": label, "risk_type": rtype, "risk_cause": cause},
            "meta": {"flags": ["reply_to_user"] if reply else []}}


def rtype(r):
    return r["gold"]["risk_type"]


def test_pick_unsafe_caps_each_type_and_spreads_over_sources():
    by_source = {
        "a": [rec(i, "UNSAFE", "PRIVACY_LEAKAGE", source="a") for i in range(80)]
             + [rec(100 + i, "UNSAFE", "DATA_LOSS", source="a") for i in range(5)],
        "b": [rec(200 + i, "UNSAFE", "PRIVACY_LEAKAGE", source="b") for i in range(10)]
             + [rec(300 + i, "UNSAFE", "SECURITY", source="b") for i in range(70)],
    }
    chosen = pick_unsafe(by_source, rtype, random.Random(1), cap=40, cause_sources=set())
    a, b = Counter(map(rtype, chosen["a"])), Counter(map(rtype, chosen["b"]))
    assert a == {"PRIVACY_LEAKAGE": 30, "DATA_LOSS": 5}           # b has only 10 privacy: a fills the rest of 40
    assert b == {"PRIVACY_LEAKAGE": 10, "SECURITY": 40}


def test_pick_unsafe_spreads_over_causes():
    pool = [rec(i, "UNSAFE", "PRIVACY_LEAKAGE", cause="UNTRUSTED_CONTENT") for i in range(50)]
    pool += [rec(100 + i, "UNSAFE", "PRIVACY_LEAKAGE", cause="AGENT_ERROR") for i in range(8)]
    chosen = pick_unsafe({"agentrisk": pool}, rtype, random.Random(1), cap=20)
    assert Counter(r["gold"]["risk_cause"] for r in chosen["agentrisk"]) == {"AGENT_ERROR": 8, "UNTRUSTED_CONTENT": 12}


def test_downsample_drops_replies_first_and_is_repeatable():
    safe = [rec(i, "SAFE", "NONE", reply=i < 90) for i in range(130)]
    picked = downsample(safe, 50, random.Random(1), lambda r: "reply_to_user" in r["meta"]["flags"])
    assert len(picked) == 50 and sum("reply_to_user" in r["meta"]["flags"] for r in picked) == 10
    a = downsample(safe, 40, random.Random(7))
    b = downsample(list(reversed(safe)), 40, random.Random(7))
    assert [r["record_id"] for r in a] == [r["record_id"] for r in b]
