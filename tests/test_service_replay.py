"""The replay website (src/service/app.py): lists and replays the demo logs; /api/live/* stays 403 (CLAUDE.md)."""
import pytest
from fastapi.testclient import TestClient

from src.service.app import DEMO_DIR, create_app
from src.service.cost_guard import APPROVAL_VAR, APPROVED

LIVE_ENV = ("LIVE_MODE", "LIVE_PASSWORD", APPROVAL_VAR)


@pytest.fixture
def client(monkeypatch):
    for name in LIVE_ENV:
        monkeypatch.delenv(name, raising=False)
    return TestClient(create_app())


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "mode": "replay", "live_mode": False,
                                            "live_available": False}


def test_workspace_is_the_home_page(client):
    res = client.get("/")
    assert res.status_code == 200 and "text/html" in res.headers["content-type"]
    assert "Northwind Labs" in res.text and "FAKE MONITOR" in res.text and "REPLAY" in res.text
    assert "Live mode is offline" in res.text


def test_event_timeline_is_still_served(client):
    res = client.get("/replay")
    assert res.status_code == 200 and "monitor ${r.monitor_version" in res.text


def test_runs_list_the_fake_demo_runs_with_agent_and_monitor(client):
    runs = [r for r in client.get("/api/runs").json() if r["source"] == "fake"]
    assert len(runs) == 7
    assert all(r["fake_monitor"] and r["agent"] == "scripted" and r["monitor_version"] == "v2" and r["k"] == 8
               for r in runs)
    always = [r for r in runs if r["setting"] == "always"]
    assert len(always) == 3 and all(r["reused_from"] for r in always)
    assert {r["decision"] for r in runs} == {"BLOCK", "ASK_CONFIRMATION"}


def test_one_run_replays_all_its_events(client):
    run = next(r for r in client.get("/api/runs").json()
               if r["source"] == "fake" and r["task"] == "demo_hidden" and r["setting"] == "selective")
    data = client.get(f"/api/runs/{run['source']}/{run['run_id']}").json()
    types = [e["type"] for e in data["events"]]
    assert types[:2] == ["company_snapshot", "instruction"] and types[-1] == "final_response"
    assert {"risk_action", "policies", "monitor_pass1", "gateway_check", "decision"} <= set(types)
    assert data["summary"]["checks_used"] == 1


@pytest.mark.parametrize("path", ["/api/runs/fake/nope", "/api/runs/fake/..%2F..%2Fsecret", "/api/runs/other/x",
                                  "/api/runs/fake/attempts"])
def test_unknown_or_unsafe_run_is_404(client, path):
    assert client.get(path).status_code == 404


def test_attempts_are_never_listed(tmp_path):
    (tmp_path / "attempts").mkdir()
    (tmp_path / "attempts" / "x__groq_try1.jsonl").write_text("{}\n")
    app = TestClient(create_app({"real": tmp_path}))
    assert app.get("/api/runs").json() == []


# --- /api/live/*: 403 without the flag, the password or the approval (CLAUDE.md, Required safety code)

def test_live_is_403_by_default(client):
    assert client.post("/api/live/run").status_code == 403
    assert client.get("/api/live/anything/else").status_code == 403


def test_live_is_403_without_password(client, monkeypatch):
    monkeypatch.setenv("LIVE_MODE", "on")
    monkeypatch.setenv("LIVE_PASSWORD", "test-only-password")
    assert client.post("/api/live/run").status_code == 403
    assert client.post("/api/live/run", headers={"X-Live-Password": "wrong"}).status_code == 403


def test_live_is_403_without_approval(client, monkeypatch):
    monkeypatch.setenv("LIVE_MODE", "on")
    monkeypatch.setenv("LIVE_PASSWORD", "test-only-password")
    res = client.post("/api/live/run", headers={"X-Live-Password": "test-only-password"})
    assert res.status_code == 403 and "Ask Prateek" in res.json()["detail"]


def test_live_stays_403_even_with_everything_because_it_is_tier_c(client, monkeypatch, tmp_path):
    import src.service.cost_guard as cg
    monkeypatch.setattr(cg, "LEDGER", tmp_path / "ledger.csv")
    monkeypatch.setenv("LIVE_MODE", "on")
    monkeypatch.setenv("LIVE_PASSWORD", "test-only-password")
    monkeypatch.setenv(APPROVAL_VAR, APPROVED)
    res = client.post("/api/live/run", headers={"X-Live-Password": "test-only-password"})
    assert res.status_code == 403 and "Tier C" in res.json()["detail"]
    assert not (tmp_path / "ledger.csv").exists()


def test_empty_password_never_matches(client, monkeypatch):
    monkeypatch.setenv("LIVE_MODE", "on")
    monkeypatch.setenv("LIVE_PASSWORD", "")
    assert client.post("/api/live/run", headers={"X-Live-Password": ""}).status_code == 403


def test_demo_dir_is_the_committed_folder():
    assert DEMO_DIR.parts[-3:] == ("outputs", "live", "demo")
