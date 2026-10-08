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
