"""Live mode of the workspace (src/service/live.py, the live routes of src/service/app.py): built, kept OFF.

Tested ONLY with the local fake backend: the rule-based fake monitor and the scripted agent, on CPU, through the
TestClient. No real account is reached (tests/conftest.py blocks the network), and the ledger is a temp file."""
import csv
import dataclasses
import json

import pytest
from fastapi.testclient import TestClient

import src.service.cost_guard as cg
from src.service.app import create_app
from src.service.cost_guard import APPROVAL_VAR, APPROVED
from src.service.live import FREE_TEXT_ID, MAX_PROMPT_CHARS, NO_SCRIPT, local_fake_backend

PASSWORD = "test-only-password"
HEADERS = {"X-Live-Password": PASSWORD}
LIVE_ROUTES = (("POST", "/api/live/run"), ("GET", "/api/live/events"), ("GET", "/api/live/state"),
               ("POST", "/v1/continue"), ("POST", "/api/live/reset"), ("GET", "/api/live/anything"))


@pytest.fixture
def ledger(monkeypatch, tmp_path):
    path = tmp_path / "ledger.csv"
    monkeypatch.setattr(cg, "LEDGER", path)
    return path


@pytest.fixture
def env(monkeypatch, ledger):
    """Everything on: the flag, the password and the approval variable (pytest only, never a real shell)."""
    monkeypatch.setenv("LIVE_MODE", "on")
    monkeypatch.setenv("LIVE_PASSWORD", PASSWORD)
    monkeypatch.setenv(APPROVAL_VAR, APPROVED)


@pytest.fixture
def client(env):
    return TestClient(create_app(live=local_fake_backend()))


def start(client, **body):
    res = client.post("/api/live/run", json=body, headers=HEADERS)
    assert res.status_code == 200, res.text
    return res.json()["session"]


def session(client, sid):
    return client.app.state.live_sessions.get(sid)


def stream(client, sid, after=0):
    """(events, summaries, saw the end frame) of the whole SSE stream; only called when the run can finish."""
    text = client.get("/api/live/events", params={"session": sid, "after": after}, headers=HEADERS).text
    events, summaries, end = [], [], False
    for block in text.strip().split("\n\n"):
        lines = block.split("\n")
        data = json.loads(next(line[6:] for line in lines if line.startswith("data: ")))
        if "event: summary" in lines:
            summaries.append(data)
        elif "event: end" in lines:
            end = True
        else:
            events.append(data)
    return events, summaries, end


# --- off by default (CLAUDE.md, Required safety code)

@pytest.mark.parametrize("method,path", LIVE_ROUTES)
def test_served_app_has_no_backend_so_every_live_route_is_403(env, ledger, method, path):
    app = TestClient(create_app())                       # what `python -m src.service.app` serves
    assert app.get("/health").json()["live_available"] is False
    res = app.request(method, path, headers=HEADERS, json={} if method == "POST" else None)
    assert res.status_code == 403 and "Tier C" in res.json()["detail"]
    assert not ledger.exists()


@pytest.mark.parametrize("method,path", LIVE_ROUTES)
@pytest.mark.parametrize("missing", ["flag", "password", "approval"])
def test_fake_backend_is_403_without_the_flag_the_password_or_the_approval(client, monkeypatch, ledger, method, path,
                                                                           missing):
    headers = dict(HEADERS)
    if missing == "flag":
        monkeypatch.setenv("LIVE_MODE", "off")
    elif missing == "password":
        headers = {"X-Live-Password": "wrong"}
    else:
        monkeypatch.delenv(APPROVAL_VAR)
    res = client.request(method, path, headers=headers, json={"task_id": "demo_hidden"} if method == "POST" else None)
    assert res.status_code == 403
    assert not ledger.exists() and not client.app.state.live_sessions._sessions


def test_health_says_available_only_with_a_backend_and_the_flag(client, monkeypatch):
    assert client.get("/health").json()["live_available"] is True
    monkeypatch.setenv("LIVE_MODE", "off")
    assert client.get("/health").json()["live_available"] is False


def test_a_backend_on_real_accounts_is_always_refused(env, ledger):
    paid = dataclasses.replace(local_fake_backend(), paid=True)
    app = TestClient(create_app(live=paid))
    res = app.post("/api/live/run", json={"task_id": "demo_hidden"}, headers=HEADERS)
    assert res.status_code == 403 and "Tier C" in res.json()["detail"]
    assert not ledger.exists() and not app.app.state.live_sessions._sessions


# --- a live run on the fake backend

def test_a_preset_task_runs_live_and_streams_the_same_events_as_a_recording(client, ledger):
    sid = start(client, task_id="demo_hidden", setting="selective")
    events, summaries, end = stream(client, sid)
    types = [e["type"] for e in events]
    assert types[:2] == ["company_snapshot", "instruction"] and types[-1] == "final_response" and end
    assert {"risk_action", "policies", "monitor_pass1", "gateway_check", "decision", "action_refused"} <= set(types)
    meta = events[1]["payload"]["meta"]
    assert meta["live"] is True and meta["fake_monitor"] is True and meta["agent"] == "scripted"
    assert meta["monitor_version"] == "v2" and meta["k"] == 8
    assert summaries[-1]["decision"] == "BLOCK" and summaries[-1]["checks_used"] == 1
    assert summaries[-1]["source"] == "live" and summaries[-1]["fake_monitor"] is True
    rows = list(csv.DictReader(ledger.open()))           # one $0 row per run, written before the run
    assert len(rows) == 1 and rows[0]["tier"] == "B" and float(rows[0]["est_max_usd"]) == 0.0
    assert "local fake" in rows[0]["service"]


def test_stream_can_resume_after_an_event_index(client):
    sid = start(client, task_id="demo_visible", setting="always")
    events, _, _ = stream(client, sid)
    rest, _, end = stream(client, sid, after=len(events) - 2)
    assert rest == events[-2:] and end


def test_state_endpoint_follows_the_live_session(client):
    sid = start(client, task_id="demo_hidden")
    stream(client, sid)
    state = client.get("/api/live/state", params={"session": sid}, headers=HEADERS).json()
    assert "/project/report_7.pdf" in state["state"]["files"]            # the fake monitor blocked the delete
    assert client.get("/api/live/state", params={"session": "nope"}, headers=HEADERS).status_code == 404


# --- Approve / Deny -> POST /v1/continue

@pytest.mark.parametrize("answer,outcome,deleted", [("yes", "action_applied", True), ("no", "action_refused", False)])
def test_approve_and_deny_answer_the_pending_confirmation(client, answer, outcome, deleted):
    sid = start(client, task_id="demo_acmepay", setting="selective")
    run = session(client, sid)
    assert run.wait_for("confirm_request") and not run.done              # the run is paused, waiting for the page
    res = client.post("/v1/continue", json={"session": sid, "answer": answer}, headers=HEADERS)
    assert res.status_code == 200 and res.json()["answer"] == answer
    events, _, end = stream(client, sid)
    types = [e["type"] for e in events]
    assert end and outcome in types
    assert next(e for e in events if e["type"] == "confirm_answer")["payload"]["answer"] == answer
    state = client.get("/api/live/state", params={"session": sid}, headers=HEADERS).json()["state"]
    assert ("AcmePay" not in state["repos"]) is deleted


def test_continue_needs_a_pending_confirmation_and_a_yes_or_no(client):
    sid = start(client, task_id="demo_hidden")
    stream(client, sid)                                                  # finished, nothing pending
    post = lambda body: client.post("/v1/continue", json=body, headers=HEADERS).status_code   # noqa: E731
    assert post({"session": sid, "answer": "yes"}) == 409
    assert post({"session": sid, "answer": "maybe"}) == 400
    assert post({"session": "nope", "answer": "yes"}) == 404
    assert client.post("/v1/continue", content="not json", headers=HEADERS).status_code == 400


def test_an_unanswered_confirmation_is_denied(client):
    client.app.state.live_sessions.confirm_timeout_s = 0.2
    sid = start(client, task_id="demo_acmepay")
    events, _, _ = stream(client, sid)                                   # ends by itself after the timeout
    types = [e["type"] for e in events]
    assert "action_refused" in types and "action_applied" not in types
    assert next(e for e in events if e["type"] == "confirm_answer")["payload"]["answer"] == "no"


# --- fresh state per session, and Reset company

def test_every_session_gets_its_own_fresh_company(client):
    first = start(client, task_id="demo_acmepay")
    assert session(client, first).wait_for("confirm_request")
    client.post("/v1/continue", json={"session": first, "answer": "yes"}, headers=HEADERS)
    stream(client, first)                                                # AcmePay is deleted in the first session
    second = start(client, task_id="demo_acmepay")
    assert session(client, second).wait_for("confirm_request")
    snapshot = session(client, second).events[0]
    assert snapshot["type"] == "company_snapshot" and "AcmePay" in snapshot["payload"]["state"]["repos"]
    client.post("/api/live/reset", json={"session": second}, headers=HEADERS)


def test_reset_drops_the_session_and_returns_the_fresh_company(client):
    sid = start(client, task_id="demo_acmepay")
    run = session(client, sid)
    assert run.wait_for("confirm_request")
    res = client.post("/api/live/reset", json={"session": sid}, headers=HEADERS)
    data = res.json()
    assert res.status_code == 200 and data["reset"] is True
    assert [e["type"] for e in data["events"]] == ["company_snapshot"]
    assert "AcmePay" in data["events"][0]["payload"]["state"]["repos"] and data["events"][0]["payload"]["overrides"] == {}
    assert session(client, sid) is None
    run._thread.join(5)
    assert run.done and "action_applied" not in [e["type"] for e in run.events]      # the pending request was denied
    again = client.post("/api/live/reset", json={}, headers=HEADERS).json()
    assert again["reset"] is False and again["events"][0]["type"] == "company_snapshot"


def test_too_many_runs_at_once_are_refused(client):
    running = [start(client, task_id="demo_acmepay") for _ in range(2)]
    assert all(session(client, sid).wait_for("confirm_request") for sid in running)
    res = client.post("/api/live/run", json={"task_id": "demo_acmepay"}, headers=HEADERS)
    assert res.status_code == 429
    for sid in running:
        client.post("/api/live/reset", json={"session": sid}, headers=HEADERS)


# --- free-text tasks: only in live mode, behind the password

def test_free_text_task_runs_only_through_the_live_route(client):
    sid = start(client, prompt="  Archive the   old-prototype repository.  ")
    events, summaries, end = stream(client, sid)
    instruction = next(e for e in events if e["type"] == "instruction")["payload"]
    assert instruction["task_id"] == FREE_TEXT_ID and instruction["prompt"] == "Archive the old-prototype repository."
    assert events[0]["payload"]["overrides"] == {}                       # the plain seed company
    assert events[-1]["payload"] == {"status": "done", "text": NO_SCRIPT} and end      # the fake agent says so
    assert summaries[-1]["decision"] is None


@pytest.mark.parametrize("body,status", [({"prompt": "   "}, 400), ({"prompt": "x" * (MAX_PROMPT_CHARS + 1)}, 400),
                                         ({"task_id": "no_such_task"}, 404),
                                         ({"task_id": "demo_hidden", "setting": "never"}, 400), ({}, 400)])
def test_bad_run_requests_start_nothing(client, body, status):
    assert client.post("/api/live/run", json=body, headers=HEADERS).status_code == status
    assert not client.app.state.live_sessions._sessions


def test_unknown_live_route_is_404_once_the_gate_passed(client):
    assert client.get("/api/live/anything", headers=HEADERS).status_code == 404
