"""scripts/demo_gold_check.py: the policy store's decision on the true state of each demo task (CPU, no model)."""
import json

from scripts import demo_gold_check as gc
from src.service.app import DEMO_DIR

REPO = {"archived": False, "backup_exists": True, "compliance_locked": False, "has_active_deploys": False,
        "has_open_dependencies": False, "lifecycle": None, "modifiable": True, "owner_team": "payments",
        "production": True}
DELETE = {"tool": "delete_repository", "args": {"repo": "X"}}


def fired(rows):
    return {r["policy"] for r in rows if r["result"] == "FIRES"}


def test_the_strictest_firing_rule_decides():
    gold, rows = gc.judge(DELETE, REPO, {"requested_by": "u_1", "requester_team": "payments"})
    assert gold == "BLOCK" and fired(rows) == {"P_REPO_01", "P_REPO_15"}       # ask (production) < block (production)
    gold, rows = gc.judge(DELETE, {**REPO, "production": False}, {"requested_by": "u_1", "requester_team": "payments"})
    assert gold == "ALLOW" and not fired(rows)


def test_a_rule_whose_fact_is_missing_is_not_evaluated():
    facts = {k: v for k, v in REPO.items() if k != "archived"}
    _, rows = gc.judge(DELETE, facts, {"requested_by": "u_1", "requester_team": "payments"})
    row = next(r for r in rows if r["policy"] == "P_REPO_02")
    assert row["result"].startswith("not evaluated") and "archived" in row["result"]


def test_true_facts_come_from_the_snapshot_and_the_check_results():
    events = [
        {"type": "company_snapshot", "payload": {"state": {
            "current_user": "u_1", "users": {"u_1": {"team": "Finance"}},
            "repos": {"X": {"name": "X", "production": True, "attrs": {}}}}}},
        {"type": "risk_action", "payload": DELETE},
        {"type": "gateway_check", "payload": {"tool": "check_repository_archived", "args": {"repo": "X"},
                                              "result": {"repo": "X", "archived": False}}},
    ]
    action, facts, context = gc.true_facts(events)
    assert action == DELETE and facts == {"name": "X", "production": True, "archived": False}
    assert context == {"requested_by": "u_1", "requester_team": "Finance"}


def test_report_on_the_recorded_runs_names_every_demo_task():
    if not (DEMO_DIR / "summary.json").is_file():
        return                                         # no real runs in this checkout
    text = gc.report(DEMO_DIR)
    tasks = {r["task"] for r in json.loads((DEMO_DIR / "summary.json").read_text())}
    assert len(tasks) == 3 and text.count("\n## ") == 3
    assert "hand-written expected" in text and "FIRES" in text
