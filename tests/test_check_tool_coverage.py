"""scripts/check_tool_coverage.py: conditions bind requested_by / requester_team and never read a variable as text."""
import importlib.util

import pytest

from src.common.io import REPO_ROOT

_spec = importlib.util.spec_from_file_location("coverage", REPO_ROOT / "scripts" / "check_tool_coverage.py")
cov = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cov)
SEEDS = {s["seed_id"]: s for s in cov.load_seeds()}
cov.SEEDS_BY_ID.update(SEEDS)


@pytest.mark.parametrize("seed_id,variant", [("IND-FILE-T1-001", "A"), ("IND-FILE-T1-005", "A"), ("IND-REPO-T1-002", "B")])
def test_requester_rules_give_the_seed_gold(seed_id, variant):
    s = SEEDS[seed_id]
    got = {v: want for v, _, want, _, _ in cov.gold_from_policies(s)}
    assert got[variant] == cov.gold(s)[variant]


def test_owner_other_than_requester_still_blocks():
    rule = cov.LOGIC["P_FILE_03"]
    ctx = {"requested_by": "user_12"}
    assert cov.evaluate(rule, {"owner": "user_9"}, {}, ctx) is True     # BLOCK fires
    assert cov.evaluate(rule, {"owner": "user_12"}, {}, ctx) is False


def test_unbound_variable_raises_instead_of_reading_text():
    with pytest.raises(cov.UnboundName):
        cov.evaluate(cov.LOGIC["P_FILE_03"], {"owner": "user_9"}, {}, {}, "test")
