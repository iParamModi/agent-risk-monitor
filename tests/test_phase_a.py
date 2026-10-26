"""src/external/phase_a.py on synthetic records."""
import random
from collections import Counter

from src.external.phase_a import balance, downsample


def rec(i, label, rtype=None, reply=False):
    return {"record_id": f"X-{i:03d}", "source": "agentrisk", "gold": {"risk_label": label, "risk_type": rtype},
            "meta": {"flags": ["reply_to_user"] if reply else []}}


def pool():
    out = [rec(i, "UNSAFE", "PRIVACY_LEAKAGE") for i in range(100)]
    out += [rec(100 + i, "UNSAFE", "SECURITY") for i in range(20)]
    out += [rec(200 + i, "SAFE", "NONE", reply=i < 90) for i in range(130)]
    return out


def rtype(r):
    return r["gold"]["risk_type"]


def test_balance_caps_privacy_and_matches_safe():
    picked = balance(pool(), rtype, random.Random(1), cap=30, drop_first=lambda r: "reply_to_user" in r["meta"]["flags"])
    unsafe = Counter(rtype(r) for r in picked if r["gold"]["risk_label"] == "UNSAFE")
    assert unsafe == {"PRIVACY_LEAKAGE": 30, "SECURITY": 20}
    safe = [r for r in picked if r["gold"]["risk_label"] == "SAFE"]
    assert len(safe) == 50
    assert sum("reply_to_user" in r["meta"]["flags"] for r in safe) == 10      # all 40 non-replies first


def test_balance_keeps_everything_under_the_cap():
    small = [rec(i, "UNSAFE", "PRIVACY_LEAKAGE") for i in range(5)] + [rec(10 + i, "SAFE", "NONE") for i in range(5)]
    assert balance(small, rtype, random.Random(1), cap=30) == sorted(small, key=lambda r: r["record_id"])


def test_downsample_is_repeatable():
    rs = pool()
    a = downsample(rs, 40, random.Random(7))
    b = downsample(list(reversed(rs)), 40, random.Random(7))
    assert [r["record_id"] for r in a] == [r["record_id"] for r in b]
