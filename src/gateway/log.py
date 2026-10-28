"""Gateway call log: one CallLogEntry per call (decisions.md R7.6), JSONL writer, per-case summary.

Written to outputs/runs/<run_id>/gateway_log.jsonl. The evaluation reads it; the gateway computes no
gold-based metric itself.
"""
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class CallLogEntry(BaseModel):
    run_id: str
    case_id: str
    setting: Literal["never", "always", "selective", "oracle"]
    call_index: int                         # 1, 2, 3 ... order within the case, all statuses
    tool: str
    args: dict
    status: Literal["ok", "error", "blocked_write"]
    error_code: str | None                  # R7.3 / R7.4 name
    facts: dict | None
    is_retry: bool                          # this call came right after an error
    resource_matches_action: bool | None    # logged only, never blocks
    noisy: bool = False                     # A6 changed a value in this result


def write_jsonl(entries: list[CallLogEntry], path: str | Path, append: bool = True) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a" if append else "w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e.model_dump(), sort_keys=True, ensure_ascii=False) + "\n")


def summarize(entries: list[CallLogEntry]) -> dict:
    """Counts for one case: valid checks, errors, blocked writes, recovered (an error followed by a
    successful call), calls on a resource the proposed action does not name, and the tools in order."""
    recovered = any(a.status == "error" and b.status == "ok" for a, b in zip(entries, entries[1:]))
    return {"calls": len(entries),
            "valid_checks": sum(e.status == "ok" for e in entries),
            "errors": sum(e.status == "error" for e in entries),
            "blocked_writes": sum(e.status == "blocked_write" for e in entries),
            "recovered": recovered,
            "wrong_resource_calls": sum(e.resource_matches_action is False for e in entries),
            "tools": [e.tool for e in entries]}
