"""Consistency of configs/check_tools.yaml and configs/check_table.yaml with the agent tools and phases."""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def _load(rel):
    return yaml.safe_load(open(ROOT / rel, encoding="utf-8"))


CHECKS = _load("configs/check_tools.yaml")
TABLE = _load("configs/check_table.yaml")
AGENT = _load("lma_agent/tools.yaml")
PHASES = _load("configs/tool_phases.yaml")

PHASE1 = {t for group in ("phase1_in_domain", "ood_test_only") for kind in ("read", "write")
          for t in PHASES[group][kind]}
PHASE1_READ = {t for group in ("phase1_in_domain", "ood_test_only") for t in PHASES[group]["read"]}
PHASE2 = set(PHASES["phase2"]["read"]) | set(PHASES["phase2"]["write"])   # phase 2 started (Task 4)
PHASE2_READ = set(PHASES["phase2"]["read"])
DROPPED = set(PHASES["dropped"])
ENTRIES = [(action, e) for action, row in TABLE.items() for e in (row or [])]


def test_table_checks_exist():
    missing = sorted({e["check"] for _, e in ENTRIES} - set(CHECKS))
    assert not missing, f"check_table names unknown checks: {missing}"


def test_every_phase1_tool_has_a_row():
    assert not sorted(PHASE1 - set(TABLE)), "phase 1 tools without a check_table row"
    assert all(TABLE[t] == [] for t in PHASE1_READ), "read tools must have []"
    assert all(TABLE.get(t) == [] for t in PHASE2_READ), "phase 2 read tools must have []"


def test_no_dropped_phase_rows():
    assert not sorted(DROPPED & set(TABLE)), "dropped tools must not have rows"
    assert not sorted(set(TABLE) - PHASE1 - PHASE2), "rows for tools outside phase 1/2"


@pytest.mark.parametrize("action,entry", ENTRIES, ids=[f"{a}-{e['check']}" for a, e in ENTRIES])
def test_args_sources_and_targets(action, entry):
    action_params = AGENT[action]["params"]
    check = CHECKS[entry["check"]]
    for target, source in entry["args"].items():
        assert source == "$current_user" or source in action_params, f"{action} has no param {source}"
        assert target in check["params"], f"{entry['check']} has no param {target}"
    unfilled = set(check["required"]) - set(entry["args"])
    assert not unfilled, f"required params not filled: {unfilled}"
    if "if_arg" in entry:
        assert entry["if_arg"] in action_params, f"if_arg {entry['if_arg']} is not a param of {action}"


def test_check_names_differ_from_agent_tools():
    assert not sorted(set(CHECKS) & set(AGENT))


def test_revealed_by_names_real_read_tools():
    agent_read = {name for name, t in AGENT.items() if t["type"] == "read"}
    for name, check in CHECKS.items():
        if check["revealed_by"] == "none":
            continue
        for ref in check["revealed_by"].split(","):
            tool = ref.strip().split(".")[0]
            assert tool in agent_read, f"{name}: revealed_by {tool} is not an agent read tool"
