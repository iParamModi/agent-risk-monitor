"""Replay website for the recorded demo runs, and the live endpoints locked off (CLAUDE.md, Cost safety).

    uvicorn src.service.app:app --port 8000        # or: python -m src.service.app
    open http://127.0.0.1:8000/

It only replays logs: no model, no GPU, no API call. Runs come from
    outputs/live/demo/*.jsonl        real runs (kaggle/demo_record/demo_record.ipynb), source "real"
    outputs/live/demo/fake/*.jsonl   CPU fake monitor (scripts/record_demo_fake.py), source "fake": the page shows a
                                     FAKE MONITOR banner on them
Tries in attempts/ are never listed (they are kept in the folder for honesty, not replayed).

GET /                         the Northwind Labs workspace (src/service/static/workspace.html)
GET /replay                   the event timeline (src/service/static/replay.html)
GET /health                   + live_available (False: no live backend is built; Step 2, under the cost rules)
GET /api/tasks                the preset demo tasks (lma_agent/tasks/demo_tasks.yaml)
GET /api/runs                 one summary per run: task, setting, agent, monitor version and k, decision, checks
GET /api/runs/{source}/{id}   the run's events, in order
GET /api/runs/{source}/{id}/state?step=N   the company after step N (company_snapshot + state_diffs), with the
                              facts hidden from the monitor marked (for the human viewer; src/live/company.py)
GET /api/results              the report's final numbers (src/service/results.py, from final_results_v2.json)
GET /api/team                 who built which part, each part tied to its PROGRESS.md rows (src/service/team.py)
GET /report.pdf               the final report (report/final_submission.pdf)
/api/live/*  (any method)     403 unless LIVE_MODE=on AND header X-Live-Password equals LIVE_PASSWORD (constant-time
                              compare) AND the cost guard passes. The live service was cut on 12 Nov and has no priced
                              backend, so the guard is asked with Tier C and always refuses: these stay 403.
"""
import hmac
import json
import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from src.common.io import REPO_ROOT
from src.live.company import state_at
from src.service.cost_guard import PaidCallBlocked, require_paid_ok
from src.service.results import REPORT_PDF, load_results
from src.service.team import team

DEMO_DIR = REPO_ROOT / "outputs" / "live" / "demo"
DEMO_TASKS = REPO_ROOT / "lma_agent" / "tasks" / "demo_tasks.yaml"
STATIC = Path(__file__).resolve().parent / "static"
RUN_ID = re.compile(r"^[A-Za-z0-9_.-]+$")


def default_sources() -> dict[str, Path]:
    return {"real": DEMO_DIR, "fake": DEMO_DIR / "fake"}


def read_log(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def summarize(events: list[dict], source: str) -> dict:
    first = next((e for e in events if e["type"] == "instruction"), {})
    payload = first.get("payload", {})
    meta = payload.get("meta", {})
    decisions = [e["payload"] for e in events if e["type"] == "decision"]
    final = next((e["payload"] for e in reversed(events) if e["type"] == "final_response"), {})
    d = decisions[0] if decisions else {}
    return {
        "source": source, "run_id": first.get("run_id"), "task": payload.get("task_id"),
        "prompt": payload.get("prompt"),
        "setting": meta.get("setting"), "confirm": meta.get("confirm"), "agent": meta.get("agent"),
        "monitor_version": meta.get("monitor_version"), "k": meta.get("k"),
        "fake_monitor": bool(meta.get("fake_monitor")) or source == "fake", "monitor_model": meta.get("monitor_model"),
        "reused_from": meta.get("trajectory_reused_from"), "fallback_reason": meta.get("fallback_reason"),
        "agent_attempt": meta.get("agent_attempt"), "recorded_at": meta.get("recorded_at"),
        "expected": meta.get("expected"), "decision": d.get("decision"), "checks_used": d.get("checks_used"),
        "checks_always": d.get("checks_always"), "status": final.get("status"), "events": len(events),
    }


def live_available() -> bool:
    """A live backend (agent + monitor) is not built in this step: always False (Step 2, under the cost rules)."""
    return False


def create_app(sources: dict[str, Path] | None = None) -> FastAPI:
    app = FastAPI(title="Agent risk monitor: recorded demo runs", docs_url=None, redoc_url=None)
    roots = sources if sources is not None else default_sources()

    def logs() -> dict[tuple[str, str], Path]:
        out = {}
        for source, folder in roots.items():
            for path in sorted(Path(folder).glob("*.jsonl")):          # top level only: never attempts/
                out[(source, path.stem)] = path
        return out

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "replay", "live_mode": os.environ.get("LIVE_MODE", "off") == "on",
                "live_available": live_available()}

    @app.get("/api/tasks")
    def tasks():
        from lma_agent.tasks.load_tasks import load_tasks
        return [{"id": t.task_id, "title": t.title or t.task_id, "description": t.description, "domain": t.domain,
                 "prompt": t.prompt, "expected": t.expected} for t in load_tasks(DEMO_TASKS)]

    @app.get("/api/results")
    def results():
        return load_results()

    @app.get("/api/team")
    def who_built_what():
        return team()

    @app.get("/report.pdf")
    def report():
        path = REPO_ROOT / REPORT_PDF
        if not path.is_file():
            raise HTTPException(404, "the report PDF is not in this checkout")
        return FileResponse(path, media_type="application/pdf")

    @app.get("/api/runs")
    def runs():
        return [summarize(read_log(path), source) for (source, _), path in logs().items()]

    def find(source: str, run_id: str) -> Path:
        path = logs().get((source, run_id)) if RUN_ID.match(run_id) else None
        if path is None:
            raise HTTPException(404, "no such run")
        return path

    @app.get("/api/runs/{source}/{run_id}")
    def run(source: str, run_id: str):
        events = read_log(find(source, run_id))
        return {"summary": summarize(events, source), "events": events}

    @app.get("/api/runs/{source}/{run_id}/state")
    def run_state(source: str, run_id: str, step: int | None = None):
        events = read_log(find(source, run_id))
        try:
            return state_at(events, step)
        except ValueError as err:
            raise HTTPException(409, str(err))

    @app.api_route("/api/live/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def live(rest: str, request: Request):
        if os.environ.get("LIVE_MODE", "off") != "on":
            raise HTTPException(403, "live mode is off")
        expected = os.environ.get("LIVE_PASSWORD", "")
        given = request.headers.get("x-live-password", "")
        if not expected or not hmac.compare_digest(given.encode(), expected.encode()):
            raise HTTPException(403, "wrong or missing live password")
        try:
            require_paid_ok(f"live request /api/live/{rest}", "C", None, service="live monitor",
                            command=f"{request.method} /api/live/{rest}")
        except PaidCallBlocked as err:
            raise HTTPException(403, str(err))
        return JSONResponse({"detail": "the live service is not built (cut on 12 Nov)"}, status_code=501)

    @app.get("/")
    def workspace():
        return FileResponse(STATIC / "workspace.html", media_type="text/html")

    @app.get("/replay")
    def timeline():
        return FileResponse(STATIC / "replay.html", media_type="text/html")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
