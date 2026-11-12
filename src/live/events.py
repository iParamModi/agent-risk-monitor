"""Events of one live run: what the agent did and what the monitor did, in order (the replay website reads them).

    sink = JsonlSink(OUT_DIR / f"{run_id}.jsonl")
    run_agent(..., on_event=sink)          # every Event is appended as one JSON line

The run log shows only what the agent and the monitor saw, plus state_diff (what the action changed). The diff
comes from model_dump of the states before and after the action, never from the hidden fields of one resource.
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

EventType = Literal["instruction", "tool_call", "observation", "risk_action", "policies", "monitor_pass1",
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


# What the replay shows of a changed item: names and visible fields, never the hidden ones.
_SHOWN = {"files": ("path", "owner", "sharing", "modified"), "repos": ("name", "owner", "visibility", "archived"),
          "permissions": None, "accounts": ("account_id", "balance_inr"), "customers": ("customer_id", "status"),
          "folders": ("path", "sharing")}


def _shown(collection: str, item):
    fields = _SHOWN.get(collection)
    if fields is None or not isinstance(item, dict):
        return item
    return {k: item.get(k) for k in fields if k in item}


def state_diff(before, after) -> dict:
    """{"changed": bool, "changes": [{"collection", "key", "kind": added|removed|changed, "before", "after"}]}
    over the dict collections of two CompanyStates (lists such as sent/transactions: counted as added items)."""
    a, b = before.model_dump(mode="json"), after.model_dump(mode="json")
    changes = []
    for coll in sorted(set(a) | set(b)):
        x, y = a.get(coll), b.get(coll)
        if x == y:
            continue
        if isinstance(x, dict) and isinstance(y, dict):
            for key in sorted(set(x) | set(y)):
                if key not in y:
                    changes.append({"collection": coll, "key": key, "kind": "removed",
                                    "before": _shown(coll, x[key]), "after": None})
                elif key not in x:
                    changes.append({"collection": coll, "key": key, "kind": "added",
                                    "before": None, "after": _shown(coll, y[key])})
                elif x[key] != y[key]:
                    changes.append({"collection": coll, "key": key, "kind": "changed",
                                    "before": _shown(coll, x[key]), "after": _shown(coll, y[key])})
        elif isinstance(x, list) and isinstance(y, list):
            for item in y[len(x):]:
                changes.append({"collection": coll, "key": str(len(x)), "kind": "added", "before": None,
                                "after": item})
        else:
            changes.append({"collection": coll, "key": "", "kind": "changed", "before": x, "after": y})
    return {"changed": bool(changes), "changes": changes}
