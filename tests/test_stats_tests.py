"""Paired tests: Wilcoxon on checks, exact McNemar on correctness (p-values worked out by hand)."""
import pytest

from src.eval import stats_tests as st


def case(rid, seed, n_calls, right=True):
    return {"record_id": rid, "seed_id": seed, "task": "decide_action",
            "gold": {"decision": "BLOCK"},
            "output": {"type": "DECISION", "decision": "BLOCK" if right else "ALLOW",
                       "risk_label": "UNSAFE" if right else "SAFE", "risk_type": "SECURITY" if right else "NONE"},
            "calls": [{"tool": "check_file_sharing", "args": {}, "error": None}] * n_calls}


def test_records_must_match():
    with pytest.raises(ValueError):
        st.paired([case("r1", "S1", 0)], [case("r2", "S1", 0)])
    with pytest.raises(ValueError):
        st.paired([case("r1", "S1", 0), case("r1", "S1", 0)], [case("r1", "S1", 0)])


def test_wilcoxon_all_lower_by_hand():
    # 10 records, selective always 1 call fewer: exact two-sided p = 2 / 2**10
    sel = [case(f"r{i}", f"S{i}", 1) for i in range(10)]
    alw = [case(f"r{i}", f"S{i}", 2) for i in range(10)]
    r = st.wilcoxon_checks(sel, alw)
    assert r["n_nonzero"] == 10 and r["mean_a"] == 1.0 and r["mean_b"] == 2.0
    assert r["p_value"] == pytest.approx(2 / 2 ** 10)


def test_wilcoxon_no_difference_is_p_one():
    cases = [case(f"r{i}", f"S{i}", 2) for i in range(5)]
    r = st.wilcoxon_checks(cases, cases)
    assert r["n_nonzero"] == 0 and r["p_value"] == 1.0 and r["statistic"] is None


def test_wilcoxon_by_seed_averages_within_a_seed():
    # S1 has 4 records, S2 has 1: by seed there are only 2 pairs
    sel = [case(f"a{i}", "S1", 0) for i in range(4)] + [case("b", "S2", 1)]
    alw = [case(f"a{i}", "S1", 2) for i in range(4)] + [case("b", "S2", 2)]
    r = st.wilcoxon_checks(sel, alw, by="seed")
    assert r["n"] == 2 and r["mean_a"] == pytest.approx(0.5) and r["mean_b"] == 2.0
    assert r["p_value"] == pytest.approx(0.5)      # exact, 2 pairs both lower: 2 / 2**2


def test_mcnemar_only_disagreements_count_by_hand():
    # 20 both right, 6 only always right, 0 only selective right: p = 2 * 0.5**6
    sel = [case(f"r{i}", f"S{i}", 0, right=True) for i in range(20)] + \
          [case(f"w{i}", f"T{i}", 0, right=False) for i in range(6)]
    alw = [case(f"r{i}", f"S{i}", 0, right=True) for i in range(20)] + \
          [case(f"w{i}", f"T{i}", 0, right=True) for i in range(6)]
    r = st.mcnemar_correct(sel, alw)
    assert (r["n"], r["only_a_right"], r["only_b_right"]) == (26, 0, 6)
    assert r["p_value"] == pytest.approx(2 * 0.5 ** 6)


def test_mcnemar_balanced_disagreements_is_p_one():
    sel = [case("x", "S1", 0, True), case("y", "S2", 0, False)]
    alw = [case("x", "S1", 0, False), case("y", "S2", 0, True)]
    assert st.mcnemar_correct(sel, alw)["p_value"] == 1.0
    assert st.mcnemar_correct(sel, sel)["p_value"] == 1.0      # no disagreement at all


def test_mcnemar_skips_external_records():
    ext = case("e", "E1", 0)
    ext["task"] = "judge_trajectory"
    r = st.mcnemar_correct([case("x", "S1", 0), ext], [case("x", "S1", 0), ext])
    assert r["n"] == 1


def test_compare_runs_all_four_tests():
    sel = [case(f"r{i}", f"S{i // 2}", i % 2, right=i != 3) for i in range(12)]
    alw = [case(f"r{i}", f"S{i // 2}", 2) for i in range(12)]
    r = st.compare(sel, alw)
    assert r["checks"]["by_case"]["n"] == 12 and r["checks"]["by_seed"]["n"] == 6
    assert r["correct"]["by_case"]["only_b_right"] == 1 and r["correct"]["by_seed"]["n"] == 6
    assert r["checks"]["by_case"]["p_value"] < 0.01
