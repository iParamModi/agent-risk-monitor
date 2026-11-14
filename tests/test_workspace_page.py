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


# ---------- Part C: audit log, compare, results, how it works ----------

def _between(start: str, end: str) -> str:
    return PAGE[PAGE.index(start):PAGE.index(end)]


def test_the_four_pages_are_in_the_navigation():
    nav = _between("const PAGES =", "const ACTOR =")
    assert re.findall(r'\["(\w+)", "([^"]+)"\]', nav) == [("audit", "Audit log"), ("compare", "Compare"),
                                                           ("results", "Results"), ("how", "How it works")]


def test_audit_log_names_an_actor_for_every_event_type():
    from src.live.events import EVENT_TYPES
    actors = dict(re.findall(r"(\w+): \"(\w+)\"", _between("const ACTOR =", "function setView")))
    assert set(actors) == set(EVENT_TYPES)
    assert set(actors.values()) == {"user", "agent", "monitor", "gateway", "company"}


def test_results_page_types_no_number_of_its_own():
    """Every cell is the text /api/results formatted with the report's helpers; the code holds no figure."""
    code = _between("const GRID =", "// --- how it works").replace("[95% CI]", "")      # the report's own header
    assert re.findall(r"\d+\.\d", code) == [] and re.findall(r"\b\d{2,}\b", code) == []
    assert "toFixed" not in code and ".text" in code and "R.hypothesis_rule" in code
    assert 'href: "report.pdf"' in code


def test_results_page_shows_fields_the_api_has(client):
    table = client.get("/api/results").json()["tables"][0]
    row, versus = table["rows"][0], table["selective_vs_always"][0]
    code = _between("const GRID =", "// --- how it works")
    for key in re.findall(r'\["(\w+)", "[^"]+"\]', code):
        assert key in row["text"] or key in row, key
    for key in set(re.findall(r"v\.text\.(\w+)", code)):
        assert key in versus["text"], key
    for key in set(re.findall(r"\bs\.(\w+) \}\)", code)):
        assert key in row["text"], key


def test_the_four_decisions_are_worded_as_in_decisions_md():
    from src.common.io import REPO_ROOT
    rules = (REPO_ROOT / "docs" / "decisions.md").read_text(encoding="utf-8")
    info = re.findall(r'\["(\w+)", "([^"]+)", "[^"]+"\]', _between("const DECISION_INFO =", "async function renderHow"))
    assert [d for d, _ in info] == ["ALLOW", "ASK_CONFIRMATION", "BLOCK", "ESCALATE"]
    for decision, meaning in info:
        assert f"`{decision}`: {meaning[0].lower()}{meaning[1:]}" in rules, decision


def test_compare_pairs_come_from_the_recorded_reuse(client):
    """The Compare page pairs an always run with the selective run it replays; every such pair is in the API."""
    runs = client.get("/api/runs").json()
    ids = {r["run_id"]: r for r in runs}
    pairs = [(r, ids.get(r["reused_from"])) for r in runs if r["reused_from"]]
    assert len(pairs) >= 3
    for always, selective in pairs:
        assert selective and selective["setting"] == "selective" and always["setting"] == "always"
        assert selective["task"] == always["task"] and selective["confirm"] == always["confirm"]
    assert "r.reused_from" in _between("function pairs()", "function firstBlock")
