"""Recorded demo runs for the replay website (kaggle/demo_record/demo_record.ipynb runs this on a Kaggle GPU).

    budget = GroqBudget(5)
    row = record_run(task, "selective", None, model=model, embedder=embedder, out_dir=OUT,
                     groq=groq_agent, budget=budget, max_tries=3, pause_s=65)

Each demo run is first tried with the Groq agent (openai/gpt-oss-120b), up to max_tries times. A try counts when the
agent proposes the task's target write (the last of task.expected_tools, e.g. delete_file): that log is kept. If no
try reaches it (or the Groq budget is used up), the run is recorded with the scripted agent instead
(src/live/scripted_agent.py), and the log says so. Every log's first event (instruction) carries meta with:
  "agent"            "groq:<model>" or "scripted" (the replay UI shows it)
  "monitor_version"  "v2" and "k" 8, plus the rest of src.monitor.case_inputs.VERSIONS["v2"] (from the gate itself)
  "agent_attempt"    which Groq try this is; the scripted fallback has "fallback_reason" and "groq_attempts"
Tries that did not reach the target write are kept in <out_dir>/attempts/ (not replayed, kept for honesty).
Groq free tier: one pause of pause_s seconds before every Groq episode after the first, to stay under the
tokens-per-minute limit. Every Groq episode goes through the cost guard first (src/service/cost_guard.py).
"""
import shutil
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from lma_agent.agent.gate import monitor_gate
from lma_agent.agent.loop import run_agent
from lma_agent.agent.user_sim import ScriptedUser
from lma_agent.sim.models import Task
from lma_agent.sim.seed_state import apply_overrides, build_seed_state
from src.live.events import JsonlSink, new_run_id

SCRIPTED = "scripted"
DEFAULT_VERSION = "v2"           # the final system (decisions.md 2026-11-12)

# (task_id, setting, confirm). Groq tries go in this order, so the three selective runs come first.
PLAN: tuple[tuple[str, str, str | None], ...] = (
    ("demo_visible", "selective", None),
    ("demo_hidden", "selective", None),
    ("demo_acmepay", "selective", "yes"),
    ("demo_acmepay", "selective", "no"),
    ("demo_visible", "always", None),
    ("demo_hidden", "always", None),
    ("demo_acmepay", "always", "yes"),
)


def groq_name(model: str) -> str:
    """The run log's agent name for a Groq agent: groq:<model>."""
    return f"groq:{model}"


def groq_agent(task_id: str, command: str = "kaggle/demo_record/demo_record.ipynb"):
    """(client, agent name) for one Groq episode, after the cost guard allowed it (Tier B, free tier: $0)."""
    from src.service.cost_guard import require_paid_ok
    require_paid_ok(f"groq agent episode {task_id}", "B", 0.0, command=command, service="groq",
                    unit_price="free tier", price_source="https://console.groq.com/settings/billing/plans")
    from lma_agent.agent.llm import make_client
    from lma_agent.config import MODEL
    return make_client(), groq_name(MODEL)


def scripted(task_id: str):
    from src.live.scripted_agent import scripted_agent
    return scripted_agent(task_id), SCRIPTED


class GroqBudget:
    """How many Groq episodes this session may still start (shared by all runs), and whether to pause first."""

    def __init__(self, total: int):
        self.total, self.used = int(total), 0

    @property
    def left(self) -> int:
        return self.total - self.used

    def take(self) -> None:
        if self.left <= 0:
            raise RuntimeError("Groq budget used up")
        self.used += 1


def target_tool(task: Task) -> str | None:
    """The write the demo is about: the last expected tool (delete_file, delete_repository)."""
    return task.expected_tools[-1] if task.expected_tools else None


def episode(task: Task, setting: str, confirms: bool, model, embedder, client, agent_name: str, path: Path,
            run_id: str, version: str = DEFAULT_VERSION, extra_meta: dict | None = None):
    """One agent episode on a fresh seed state, every write through the real monitor. Returns (sink, result, gate)."""
    gate = monitor_gate(model, setting=setting, version=version, embedder=embedder, task=task, run_id=run_id)
    meta = {"monitor_model": model.name, "agent": agent_name, "setting": setting, **gate.settings,
            "confirm": "yes" if confirms else "no", "expected": task.expected,
            "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **(extra_meta or {})}
    state = apply_overrides(build_seed_state(task.state_seed), task.overrides)
    sink = JsonlSink(path)
    result = run_agent(task, state, client, gate=gate, user=ScriptedUser(confirms), on_event=sink, run_id=run_id,
                       meta=meta)
    return sink, result, gate


def reached(sink, tool: str | None) -> bool:
    """Did the agent propose the target write (any write when the task names none)?"""
    return any(e.type == "risk_action" and (tool is None or e.payload.get("tool") == tool) for e in sink.events)


def summarize(task: Task, sink, run_id: str, path: Path, agent: str, status: str) -> dict:
    """One row of the results table: the first judged write, its prompt sizes and latency per monitor pass."""
    decisions = [e.payload for e in sink.events if e.type == "decision"]
    passes = [e.payload for e in sink.events if e.type in ("monitor_pass1", "monitor_pass2")]
    meta = next((e.payload.get("meta", {}) for e in sink.events if e.type == "instruction"), {})
    first = decisions[0] if decisions else {}
    exp = task.expected or {}
    row = {"run_id": run_id, "task": task.task_id, "file": str(path), "agent": agent, "status": status,
           "setting": meta.get("setting"), "confirm": meta.get("confirm"),
           "monitor_version": meta.get("monitor_version"), "k": meta.get("k"),
           "decision": first.get("decision"), "expected_decision": exp.get("decision"),
           "checks_used": first.get("checks_used"), "expected_checks": exp.get("checks"),
           "checks_always": first.get("checks_always"), "policy_ids": first.get("policy_ids"),
           "risk_actions": len(decisions),
           "prompt_tokens": [p.get("tokens_in") for p in passes],
           "output_tokens": [p.get("tokens_out") for p in passes],
           "latency_s": [p.get("latency_s") for p in passes]}
    row["match"] = row["decision"] == row["expected_decision"] if row["expected_decision"] else None
    return row


def record_run(task: Task, setting: str, confirm: str | None, *, model, embedder, out_dir: str | Path,
               groq: Callable | None = groq_agent, budget: GroqBudget | None = None, max_tries: int = 3,
               pause_s: float = 65, version: str = DEFAULT_VERSION, base_meta: dict | None = None,
               sleep: Callable[[float], None] = time.sleep, log: Callable[[str], None] = print) -> dict:
    """Record one demo run: Groq up to max_tries times, else the scripted agent. Returns the summary row.

    groq: callable(task_id) -> (client, agent name), e.g. groq_agent (cost guard inside); None = scripted only.
    A PaidCallBlocked from the cost guard is NOT caught: the notebook stops instead of quietly going scripted."""
    out_dir = Path(out_dir)
    confirms = task.user_confirms if confirm is None else confirm == "yes"
    suffix = [f"confirm_{confirm}"] if confirm else []
    tool = target_tool(task)
    tries: list[dict] = []
    reason = "Groq agent off" if groq is None else None
    for attempt in range(1, max_tries + 1):
        if groq is None:
            break
        if budget is not None and budget.left <= 0:
            reason = f"Groq episode budget used up ({budget.total} this session)"
            break
        if budget is not None and budget.used > 0 and pause_s > 0:
            log(f"pause {pause_s:.0f}s (Groq tokens-per-minute limit)")
            sleep(pause_s)
        client, agent_name = groq(task.task_id)
        if budget is not None:
            budget.take()
        run_id = new_run_id(task.task_id, setting, "__".join(suffix + [f"groq_try{attempt}"]))
        path = out_dir / "attempts" / f"{run_id}.jsonl"
        sink, result, _ = episode(task, setting, confirms, model, embedder, client, agent_name, path, run_id,
                                  version, {**(base_meta or {}), "agent_attempt": attempt, "agent_max_tries": max_tries})
        ok = reached(sink, tool)
        tries.append({"attempt": attempt, "run_id": run_id, "status": result.status, "reached_target": ok,
                      "file": f"attempts/{path.name}"})
        log(f"{task.task_id} {setting} groq try {attempt}: status {result.status}, "
            f"{'proposed ' + str(tool) if ok else 'did NOT propose ' + str(tool)}")
        if ok:
            kept = out_dir / f"{run_id}.jsonl"
            shutil.copyfile(path, kept)
            row = summarize(task, sink, run_id, kept, agent_name, result.status)
            row["groq_attempts"] = tries
            return row
    if reason is None:
        reason = f"the Groq agent never proposed {tool} in {len(tries)} tries"
    client, agent_name = scripted(task.task_id)
    run_id = new_run_id(task.task_id, setting, "__".join(suffix + ["scripted"]))
    path = out_dir / f"{run_id}.jsonl"
    sink, result, _ = episode(task, setting, confirms, model, embedder, client, agent_name, path, run_id, version,
                              {**(base_meta or {}), "fallback_reason": reason, "groq_attempts": tries})
    log(f"{task.task_id} {setting}: scripted agent ({reason})")
    row = summarize(task, sink, run_id, path, agent_name, result.status)
    row["groq_attempts"], row["fallback_reason"] = tries, reason
    return row
