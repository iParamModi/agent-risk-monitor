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
                              (+ monitor_label, the short model name for the page: monitor_label below)
GET /api/runs/{source}/{id}   the run's events, in order
GET /api/runs/{source}/{id}/state?step=N   the company after step N (company_snapshot + state_diffs), with the
                              facts hidden from the monitor marked (for the human viewer; src/live/company.py)
GET /api/results              the report's final numbers (src/service/results.py, from final_results_v2.json)
GET /api/team                 who built which part, each part tied to its PROGRESS.md rows (src/service/team.py)
GET /report.pdf               the final report (report/final_submission.pdf)
Live mode (src/service/live.py) is BUILT BUT KEPT OFF: create_app() gets no live backend, so /health says
live_available false and every route below answers 403. Only tests pass a backend (the local fake, CPU, no API).
Every live route is 403 unless LIVE_MODE=on AND header X-Live-Password equals LIVE_PASSWORD (constant-time compare)
AND the cost guard passes:
  no backend, or a backend that reaches a real account   the guard is asked with Tier C and always refuses
  the local fake backend (no real account)                starting a run is a $0 Tier B ledger row; the other
                                                          routes need the same approval variable
POST /api/live/run            {"task_id": preset} or {"prompt": free text}, + "setting": a new session on its own
                              fresh simulator state; the run starts. Free-text tasks exist only here
GET  /api/live/events         ?session=&after=N: the session's events as Server-Sent Events while it runs
GET  /api/live/state          ?session=&step=N: the session's company after step N (as /api/runs/.../state)
POST /v1/continue             {"session", "answer": "yes"|"no"}: answers the pending ASK_CONFIRMATION
POST /api/live/reset          {"session"}: drops the session and returns the fresh seed company ("Reset company")
"""
import hmac
import json
import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

from src.common.io import REPO_ROOT
from src.live.company import state_at
from src.service import cost_guard
from src.service.cost_guard import APPROVAL_VAR, PaidCallBlocked, approved, require_paid_ok
from src.service.live import SETTINGS, LiveBackend, LiveSessions, free_text_task
from src.service.results import REPORT_PDF, load_results
from src.service.team import team

DEMO_DIR = REPO_ROOT / "outputs" / "live" / "demo"
DEMO_TASKS = REPO_ROOT / "lma_agent" / "tasks" / "demo_tasks.yaml"
STATIC = Path(__file__).resolve().parent / "static"
RUN_ID = re.compile(r"^[A-Za-z0-9_.-]+$")


def default_sources() -> dict[str, Path]:
    return {"real": DEMO_DIR, "fake": DEMO_DIR / "fake"}


# Which training phase an adapter dataset is: the final adapter is the 11 Nov Phase B adapter
# (docs/messages/2026-11-13_to_Prateek_adapter_path.md). An adapter that is not listed gets no phase in its label.
ADAPTER_PHASE = {"meet6868/agent-risk-adapter-final": "Phase B"}
PEFT_NAMES = {"LORA": "LoRA"}


def monitor_label(meta: dict) -> str | None:
    """Short name of the monitor model for the page header, built from the run's own meta:
    "Qwen3-8B + LoRA (Phase B)" instead of "<base>+<adapter folder on the recording machine>"."""
    if meta.get("fake_monitor"):
        return None
    config = meta.get("adapter_config") or {}
    base = config.get("base_model_name_or_path") or str(meta.get("monitor_model") or "").split("+")[0]
    if not base:
        return None
    label = base.split("/")[-1]
    if config or meta.get("adapter_dataset"):
        label += " + " + PEFT_NAMES.get(str(config.get("peft_type") or "").upper(), "adapter")
        phase = ADAPTER_PHASE.get(meta.get("adapter_dataset"))
        label += f" ({phase})" if phase else ""
    return label


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
        "monitor_label": monitor_label(meta),
        "reused_from": meta.get("trajectory_reused_from"), "fallback_reason": meta.get("fallback_reason"),
        "agent_attempt": meta.get("agent_attempt"), "recorded_at": meta.get("recorded_at"),
        "expected": meta.get("expected"), "decision": d.get("decision"), "checks_used": d.get("checks_used"),
        "checks_always": d.get("checks_always"), "status": final.get("status"), "events": len(events),
    }


def live_available(backend: LiveBackend | None = None) -> bool:
    """True only for an app that was built with a live backend, while LIVE_MODE is on. create_app() has no backend
    (a live backend against real accounts is Step 2, under the cost rules), so the served site always says False."""
    return backend is not None and os.environ.get("LIVE_MODE", "off") == "on"


def sse(data: dict, event: str | None = None, id: int | None = None) -> str:
    head = (f"event: {event}\n" if event else "") + (f"id: {id}\n" if id is not None else "")
    return f"{head}data: {json.dumps(data, ensure_ascii=False)}\n\n"


def create_app(sources: dict[str, Path] | None = None, live: LiveBackend | None = None) -> FastAPI:
    """live: a live backend (src/service/live.py). None (the default, and the served app) keeps live mode off."""
    app = FastAPI(title="Agent risk monitor: recorded demo runs", docs_url=None, redoc_url=None)
    roots = sources if sources is not None else default_sources()
    sessions = LiveSessions(live) if live is not None else None
    app.state.live_sessions = sessions

    def logs() -> dict[tuple[str, str], Path]:
        out = {}
        for source, folder in roots.items():
            for path in sorted(Path(folder).glob("*.jsonl")):          # top level only: never attempts/
                out[(source, path.stem)] = path
        return out

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "replay", "live_mode": os.environ.get("LIVE_MODE", "off") == "on",
                "live_available": live_available(live)}

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

    # --- live mode: built, kept off (see the module docstring and src/service/live.py)

    def live_gate(request: Request, action: str, starts_run: bool = False) -> LiveSessions:
        """403 unless LIVE_MODE=on AND the password matches AND the cost guard passes. Returns the sessions."""
        if os.environ.get("LIVE_MODE", "off") != "on":
            raise HTTPException(403, "live mode is off")
        expected = os.environ.get("LIVE_PASSWORD", "")
        given = request.headers.get("x-live-password", "")
        if not expected or not hmac.compare_digest(given.encode(), expected.encode()):
            raise HTTPException(403, "wrong or missing live password")
        try:
            if live is None or live.paid:       # a backend on real accounts is Step 2: Tier C, always refused
                require_paid_ok(f"live request {action}", "C", None, service="live monitor", command=action)
            elif starts_run:                    # the local fake: no real account, a $0 row per run
                require_paid_ok(f"live run on the {live.name} backend", "B", 0.0, command=action,
                                service="none (local fake backend, no real account)", unit_price="0",
                                price_source="local CPU, no provider", ledger=cost_guard.LEDGER)
            elif not approved():
                raise PaidCallBlocked(f"live request {action}: real accounts are off ({APPROVAL_VAR} is not "
                                      f"approved). Ask Prateek.")
        except PaidCallBlocked as err:
            raise HTTPException(403, str(err))
        return sessions

    async def body_of(request: Request) -> dict:
        try:
            data = await request.json()
        except Exception:
            data = None
        if not isinstance(data, dict):
            raise HTTPException(400, "the request body must be a JSON object")
        return data

    def session_of(live_sessions: LiveSessions, session_id):
        session = live_sessions.get(session_id) if isinstance(session_id, str) else None
        if session is None:
            raise HTTPException(404, "no such live session")
        return session

    @app.post("/api/live/run")
    async def live_run(request: Request):
        live_sessions = live_gate(request, "POST /api/live/run", starts_run=True)
        data = await body_of(request)
        setting = data.get("setting", "selective")
        if setting not in SETTINGS:
            raise HTTPException(400, f"setting must be one of {list(SETTINGS)}")
        if data.get("task_id"):
            from lma_agent.tasks.load_tasks import load_tasks
            task = next((t for t in load_tasks(DEMO_TASKS) if t.task_id == data["task_id"]), None)
            if task is None:
                raise HTTPException(404, "no such preset task")
        else:
            try:
                task = free_text_task(data.get("prompt", ""))
            except ValueError as err:
                raise HTTPException(400, str(err))
        try:
            session = live_sessions.start(task, setting)
        except RuntimeError as err:
            raise HTTPException(429, str(err))
        return {"session": session.id, "run_id": session.run_id, "task": task.task_id, "setting": setting,
                "backend": live.name}

    @app.get("/api/live/events")
    def live_events(request: Request, session: str = "", after: int = 0):
        run = session_of(live_gate(request, "GET /api/live/events"), session)

        def frames():
            sent = max(0, after)
            for event in run.stream(after):
                if event is None:
                    yield ": keep-alive\n\n"
                    continue
                sent += 1
                yield sse(event, id=sent)
                if event["type"] in ("instruction", "decision", "final_response"):
                    yield sse(summarize(run.events, "live"), event="summary")
            yield sse({"events": len(run.events)}, event="end")

        return StreamingResponse(frames(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    @app.get("/api/live/state")
    def live_state(request: Request, session: str = "", step: int | None = None):
        run = session_of(live_gate(request, "GET /api/live/state"), session)
        try:
            return state_at(list(run.events), step)
        except ValueError as err:
            raise HTTPException(409, str(err))

    @app.post("/v1/continue")
    async def live_continue(request: Request):
        live_sessions = live_gate(request, "POST /v1/continue")
        data = await body_of(request)
        if data.get("answer") not in ("yes", "no"):
            raise HTTPException(400, 'answer must be "yes" or "no"')
        run = session_of(live_sessions, data.get("session"))
        if not run.answer(data["answer"] == "yes"):
            raise HTTPException(409, "this session is not waiting for a confirmation")
        return {"session": run.id, "answer": data["answer"]}

    @app.post("/api/live/reset")
    async def live_reset(request: Request):
        live_sessions = live_gate(request, "POST /api/live/reset")
        data = await body_of(request)
        dropped = live_sessions.reset(data.get("session") if isinstance(data.get("session"), str) else None)
        return {"reset": dropped, "events": [live_sessions.fresh_company()]}

    @app.api_route("/api/live/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def live_other(rest: str, request: Request):
        live_gate(request, f"{request.method} /api/live/{rest}")
        raise HTTPException(404, "no such live route")

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
