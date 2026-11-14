"""The Northwind Labs workspace page (src/service/static/workspace.html) obeys the honesty rules of Step 1b: every
decision, check result and company fact it shows comes from a run log or the API, never from the page itself."""
import json
import re

import pytest
from fastapi.testclient import TestClient

from src.service.app import DEMO_DIR, STATIC, create_app
from src.service.cost_guard import APPROVAL_VAR

PAGE = (STATIC / "workspace.html").read_text(encoding="utf-8")
LOGS = sorted(DEMO_DIR.glob("*.jsonl")) + sorted((DEMO_DIR / "fake").glob("*.jsonl"))


def _strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for k, x in v.items():
            yield from _strings(k)
            yield from _strings(x)
    elif isinstance(v, list):
        for x in v:
            yield from _strings(x)


def _run_values() -> set[str]:
    """Values a page could only know by copying them from a run: check results, evidence, policies, tool args."""
    out = set()
    for path in LOGS:
        for line in path.read_text(encoding="utf-8").splitlines():
            e = json.loads(line)
            p = e["payload"]
            if e["type"] in {"gateway_check", "decision", "policies", "risk_action", "tool_call", "observation",
                             "confirm_request", "action_refused", "action_applied", "monitor_pass1", "monitor_pass2"}:
                out |= {s for s in _strings(p) if len(s) >= 6 and not s.isidentifier()}
            if e["type"] == "decision":
                out |= set(p.get("policy_ids") or []) | set(p.get("evidence") or [])
    return out


def test_there_are_logs_to_check():
    assert len(LOGS) >= 7


def test_page_has_no_value_copied_from_a_run():
    values = _run_values()
    assert values, "no run values found"
    leaked = sorted(v for v in values if v in PAGE)
    assert leaked == []


def test_page_names_no_policy_id_or_company_record():
    assert re.findall(r"\bP_[A-Z]+_\d+\b", PAGE) == []
    for word in ("report_7", "AcmePay", "globex", "u_riya", "external:"):
        assert word not in PAGE


def test_page_is_self_contained():
    """No build step and no CDN: the demo works offline."""
    assert "<script src" not in PAGE and "<link" not in PAGE
    assert re.findall(r"https?://", PAGE) == []


@pytest.fixture
def client(monkeypatch):
    for name in ("LIVE_MODE", "LIVE_PASSWORD", APPROVAL_VAR):
        monkeypatch.delenv(name, raising=False)
    return TestClient(create_app())


def test_every_api_path_the_page_calls_exists(client):
    paths = set(re.findall(r'api\(\s*[`"]([^`"$]+)', PAGE))
    assert {"api/runs", "api/tasks", "health"} <= paths
    for p in paths:
        assert client.get("/" + p.rstrip("/")).status_code == 200, p
    run = client.get("/api/runs").json()[0]
    assert client.get(f"/api/runs/{run['source']}/{run['run_id']}/state?step=2").status_code == 200


def test_approve_and_deny_are_disabled_in_replay():
    block = PAGE[PAGE.index('class: "approve"'):PAGE.index('class: "approve"') + 400]
    assert block.count("disabled: true") == 2


def test_free_text_task_box_is_off_in_replay():
    assert re.search(r'<input id="taskinput" disabled', PAGE)
