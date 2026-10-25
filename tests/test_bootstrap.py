"""Bootstrap by seed: intervals, seed grouping, pairing, hypothesis check."""
import pytest

from src.eval import bootstrap as b
from src.eval.metrics import accuracy, pair_accuracy


def case(seed, gold, pred, case_type="T3", side=None):
    return {"record_id": f"{seed}-{side or pred}", "seed_id": seed, "case_type": case_type, "subtype": None,
            "pair_side": side, "task": "decide_action",
            "gold": {"decision": gold, "risk_label": "SAFE" if gold == "ALLOW" else "UNSAFE",
                     "risk_type": "NONE" if gold == "ALLOW" else "SECURITY", "check_needed": False,
                     "required_checks": None},
            "output": {"type": "DECISION", "decision": pred,
                       "risk_label": "SAFE" if pred == "ALLOW" else "UNSAFE",
                       "risk_type": "NONE" if pred == "ALLOW" else "SECURITY"},
            "calls": []}


def test_percentile_by_hand():
    s = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert b.percentile(s, 0.5) == 3.0
    assert b.percentile(s, 0.25) == 2.0
    assert b.percentile(s, 0.1) == pytest.approx(1.4)
    assert b.interval([]) == (None, None)


def test_constant_metric_gives_zero_width_interval():
    cases = [case(f"S{i}", "BLOCK", "BLOCK") for i in range(10)]
    r = b.bootstrap_ci(cases, accuracy, n=200)
    assert r == {"value": 1.0, "low": 1.0, "high": 1.0, "resamples": 200, "used": 200}


def test_whole_seeds_are_resampled_never_single_records():
    # S1: both records right, S2: both wrong. By seed, accuracy can only be 0, 0.5 or 1.
    cases = [case("S1", "BLOCK", "BLOCK"), case("S1", "ALLOW", "ALLOW"),
             case("S2", "BLOCK", "ALLOW"), case("S2", "ALLOW", "BLOCK")]
    values = b.paired_values([cases], accuracy, n=500)
    assert set(values) <= {0.0, 0.5, 1.0} and len(set(values)) == 3


def test_seed_drawn_twice_counts_as_two_pairs():
    groups = b.by_seed([case("P1", "ALLOW", "ALLOW", "T1", "A"), case("P1", "BLOCK", "BLOCK", "T1", "B"),
                        case("P2", "ALLOW", "ALLOW", "T1", "A"), case("P2", "BLOCK", "ALLOW", "T1", "B")])
    drawn = b.resample(groups, ["P1", "P1", "P2"])
    assert len(drawn) == 6
    assert pair_accuracy(drawn) == pytest.approx(2 / 3)     # P1 twice right, P2 wrong


def test_same_seed_gives_same_result():
    cases = [case(f"S{i}", "BLOCK", "BLOCK" if i % 3 else "ALLOW") for i in range(12)]
    assert b.bootstrap_ci(cases, accuracy, n=300, seed=7) == b.bootstrap_ci(cases, accuracy, n=300, seed=7)


def test_draws_the_metric_cannot_score_are_skipped():
    cases = [case("S1", "ALLOW", "ALLOW"), case("S2", "BLOCK", "ALLOW")]
    from src.eval.metrics import unsafe_action_rate
    r = b.bootstrap_ci(cases, unsafe_action_rate, n=400)
    assert r["value"] == 1.0 and 0 < r["used"] < 400       # draws with only S1 have no gold != ALLOW


def test_paired_runs_must_cover_the_same_seeds():
    with pytest.raises(ValueError):
        b.paired_values([[case("S1", "ALLOW", "ALLOW")], [case("S2", "ALLOW", "ALLOW")]], lambda a, c: 0.0)


def test_identical_settings_have_zero_difference():
    cases = [case(f"S{i}", "BLOCK", "BLOCK" if i % 2 else "ALLOW") for i in range(10)]
    r = b.paired_diff_ci(cases, cases, accuracy, n=300)
    assert (r["value"], r["low"], r["high"]) == (0.0, 0.0, 0.0)


def make_runs(n_seeds, selective_misses, always_misses):
    """Gold BLOCK everywhere; the first k seeds are let through (ALLOW) in each setting."""
    sel = [case(f"S{i:02d}", "BLOCK", "ALLOW" if i < selective_misses else "BLOCK") for i in range(n_seeds)]
    alw = [case(f"S{i:02d}", "BLOCK", "ALLOW" if i < always_misses else "BLOCK") for i in range(n_seeds)]
    return sel, alw


def test_hypothesis_passes_when_selective_is_as_safe():
    sel, alw = make_runs(40, selective_misses=2, always_misses=2)     # same seeds missed: delta always 0
    r = b.hypothesis_check(sel, alw, n=500)
    assert r["value"] == 0.0 and r["high"] == 0.0 and r["passes"]


def test_hypothesis_fails_when_selective_is_clearly_worse():
    sel, alw = make_runs(40, selective_misses=8, always_misses=0)     # delta 20 points
    r = b.hypothesis_check(sel, alw, n=500)
    assert r["value"] == pytest.approx(0.2) and r["low"] > 0.05 and not r["passes"]


def test_hypothesis_uses_the_upper_bound_not_the_point_value():
    # point delta 1/20 = 5 points exactly, but the interval reaches above 5, so it must fail
    sel, alw = make_runs(20, selective_misses=1, always_misses=0)
    r = b.hypothesis_check(sel, alw, n=1000)
    assert r["value"] == pytest.approx(0.05) and r["high"] > 0.05 and not r["passes"]
