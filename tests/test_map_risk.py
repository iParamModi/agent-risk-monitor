"""src/external/map_risk.py: ATBench harm -> risk_type."""
import pytest

from src.external.map_risk import MAP_FILE, atbench_risk_type, load_map

M = {
    "harm_to_type": {"security_and_system_integrity_harm": "SECURITY", "physical_and_health_harm": "OTHER"},
    "failure_mode_overrides_for_other": {"unauthorized_information_disclosure": "PRIVACY_LEAKAGE"},
    "record_overrides": {"ATB-9": "DATA_LOSS"},
}


def rec(rid, harm, fm="x"):
    return {"record_id": rid, "gold": {"risk_label": "UNSAFE",
            "source_taxonomy": {"risk_source": "s", "failure_mode": fm, "real_world_harm": harm}}}


def test_harm_map():
    assert atbench_risk_type(rec("ATB-1", "security_and_system_integrity_harm"), M) == "SECURITY"


def test_failure_mode_rule_only_for_other():
    assert atbench_risk_type(rec("ATB-1", "physical_and_health_harm", "unauthorized_information_disclosure"), M) == "PRIVACY_LEAKAGE"
    assert atbench_risk_type(rec("ATB-1", "physical_and_health_harm"), M) == "OTHER"
    # rule never changes a non-OTHER harm
    assert atbench_risk_type(rec("ATB-1", "security_and_system_integrity_harm", "unauthorized_information_disclosure"), M) == "SECURITY"


def test_record_override_wins():
    assert atbench_risk_type(rec("ATB-9", "security_and_system_integrity_harm"), M) == "DATA_LOSS"


def test_unknown_harm_fails():
    with pytest.raises(KeyError):
        atbench_risk_type(rec("ATB-1", "new_harm"), M)


def test_real_map_file_is_valid_and_complete():
    m = load_map(MAP_FILE)
    assert len(m["harm_to_type"]) == 10


def test_cohen_kappa():
    from src.external.map_risk import cohen_kappa
    assert cohen_kappa(["A", "B", "A", "B"], ["A", "B", "A", "B"]) == 1.0
    assert cohen_kappa(["A", "A", "B", "B"], ["A", "B", "A", "B"]) == 0.0  # chance level
    assert cohen_kappa(["A", "A"], ["A", "A"]) == 1.0


def _csv(path, header, rows):
    import csv
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def test_recheck_overrides_review(tmp_path):
    from src.external.map_risk import load_human_types
    review, recheck = tmp_path / "review.csv", tmp_path / "recheck.csv"
    _csv(review, ["record_id", "human_final"], [["RJ-a-1", "SECURITY"], ["RJ-a-2", "OTHER"], ["RJ-a-3", ""]])
    _csv(recheck, ["record_id", "recheck_type"], [["RJ-a-1", "PRIVACY_LEAKAGE"], ["RJ-a-2", ""], ["RJ-a-4", "DATA_LOSS"]])
    assert load_human_types(review, recheck) == {"RJ-a-1": "PRIVACY_LEAKAGE", "RJ-a-2": "OTHER", "RJ-a-4": "DATA_LOSS"}
    assert load_human_types(review, tmp_path / "none.csv") == {"RJ-a-1": "SECURITY", "RJ-a-2": "OTHER"}
    _csv(recheck, ["record_id", "recheck_type"], [["RJ-a-1", "privacy"]])
    with pytest.raises(ValueError):
        load_human_types(review, recheck)


def test_map_rjudge_reports_missing_used():
    from src.external.map_risk import map_rjudge
    def rj(rid, label):
        return {"record_id": rid, "seed_id": "RJ-scn-a", "source": "r_judge", "set": "external", "split": "train",
                "domain": None, "case_type": None, "subtype": None, "pair_side": None, "version": None, "task": "judge_trajectory",
                "visible": {"trajectory": [{"role": "user", "text": "x", "tool_call": None, "action_text": None}], "proposed_action": None},
                "hidden": None,
                "gold": {"decision": None, "risk_label": label, "risk_type": "NONE" if label == "SAFE" else None, "risk_cause": None,
                         "check_needed": None, "required_checks": None, "missing_fact": None, "policy_ids": None, "evidence": None,
                         "source_note": None, "source_taxonomy": None},
                "meta": {"n_tokens": None, "ood_shift": []}}
    recs = [rj("RJ-a-1", "UNSAFE"), rj("RJ-a-2", "UNSAFE"), rj("RJ-a-3", "UNSAFE"), rj("RJ-a-4", "SAFE")]
    counts, missing = map_rjudge(recs, {"RJ-a-1": "SECURITY"}, used={"RJ-a-1", "RJ-a-2", "RJ-a-4"})
    assert counts == {"SECURITY": 1} and missing == ["RJ-a-2"]       # RJ-a-3 is unused, so not reported
    assert recs[3]["gold"]["risk_type"] == "NONE"
