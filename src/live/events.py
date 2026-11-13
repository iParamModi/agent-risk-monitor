"""Events of one live run: what the agent did and what the monitor did, in order (the replay website reads them).

    sink = JsonlSink(OUT_DIR / f"{run_id}.jsonl")
    run_agent(..., on_event=sink)          # every Event is appended as one JSON line

The run log is for the HUMAN viewer (the replay website). It starts with company_snapshot (the full initial company
state and which facts are hidden from the monitor, src/live/company.py) and has a state_diff after every write
(what the action changed, as full rows, so src.live.company.state_at rebuilds the exact state at any step). The
monitor never reads the run log: its prompt is built from the visible record and gateway results only.
"""
import json
import re
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from src.common.io import REPO_ROOT

OUT_DIR = REPO_ROOT / "outputs" / "live"

EventType = Literal["company_snapshot", "instruction", "tool_call", "observation", "risk_action", "policies",
                    "monitor_pass1",
                    "gateway_check", "monitor_pass2", "decision", "confirm_request", "confirm_answer",
                    "action_applied", "action_refused", "state_diff", "final_response"]
EVENT_TYPES: tuple[str, ...] = EventType.__args__


class Event(BaseModel):
    run_id: str
    step: int
    ts: float
    type: EventType
    payload: dict = {}


Emit = Callable[[Event], None]


def make_event(run_id: str, step: int, type: str, payload: dict | None = None) -> Event:
    return Event(run_id=run_id, step=step, ts=round(time.time(), 3), type=type, payload=payload or {})


def new_run_id(task_id: str, setting: str, suffix: str = "") -> str:
    """demo_hidden__selective__20261112T101500Z (+ __<suffix>, e.g. confirm_no)."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parts = [task_id, setting] + ([suffix] if suffix else []) + [stamp]
    return "__".join(re.sub(r"[^A-Za-z0-9_.-]", "_", p) for p in parts)


class JsonlSink:
    """Appends each event as one JSON line (outputs/live/<run_id>.jsonl by default) and keeps them in memory."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("", encoding="utf-8")
        self.events: list[Event] = []

    def __call__(self, event: Event) -> None:
        self.events.append(event)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(event.model_dump_json() + "\n")


class ListSink:
    """Keeps events in memory only (tests)."""

    def __init__(self):
        self.events: list[Event] = []

    def __call__(self, event: Event) -> None:
        self.events.append(event)

    def types(self) -> list[str]:
        return [e.type for e in self.events]


def read_events(path: str | Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def state_diff(before, after) -> dict:
    """{"changed": bool, "changes": [{"collection", "key", "kind", "before", "after"}]} between two CompanyStates,
    exact enough to rebuild `after` from `before` (src.live.company.apply_diff):
      dict collections: one change per key, kind added | removed | changed, with the full rows
      lists (inbox, sent, transactions, ...): appended items as kind "added"; any other change replaces the list
      other fields (current_user): kind "replaced" with the whole value."""
    a, b = before.model_dump(mode="json"), after.model_dump(mode="json")
    changes = []
    for coll in sorted(set(a) | set(b)):
        x, y = a.get(coll), b.get(coll)
        if x == y:
            continue
        if isinstance(x, dict) and isinstance(y, dict):
            for key in sorted(set(x) | set(y)):
                if key not in y:
                    changes.append({"collection": coll, "key": key, "kind": "removed", "before": x[key], "after": None})
                elif key not in x:
                    changes.append({"collection": coll, "key": key, "kind": "added", "before": None, "after": y[key]})
                elif x[key] != y[key]:
                    changes.append({"collection": coll, "key": key, "kind": "changed", "before": x[key],
                                    "after": y[key]})
        elif isinstance(x, list) and isinstance(y, list) and y[:len(x)] == x:
            for i, item in enumerate(y[len(x):], start=len(x)):
                changes.append({"collection": coll, "key": str(i), "kind": "added", "before": None, "after": item})
        else:
            changes.append({"collection": coll, "key": "", "kind": "replaced", "before": x, "after": y})
    return {"changed": bool(changes), "changes": changes}


def first_of(events: list[dict], type: str) -> dict:
    """The first event of a type in a read log (company_snapshot comes before instruction since 13 Nov)."""
    return next(e for e in events if e["type"] == type)
