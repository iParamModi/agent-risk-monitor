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
The Groq episode budget is DEFAULT_GROQ_BUDGET (5, CLAUDE.md Tier B) unless a caller passes another.

Fair comparison (REUSE_FROM): an "always" run starts NO new agent episode. It replays the exact agent messages of
the same task's "selective" run (same confirm answer) up to and including the first risky action, then the agent
closes with a fixed message (CLOSING). So only the monitor setting differs. Its meta says
"trajectory_reused_from": <selective run_id>, and "agent" stays the agent that produced the trajectory.
Every kept log has a sidecar <run_id>.agent.json with the agent's own messages (what the reuse replays).
"""
import shutil
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from lma_agent.agent.gate import monitor_gate
from lma_agent.agent.llm import FakeLLM, assistant_msg, parse_tool_calls
from lma_agent.agent.loop import run_agent
from lma_agent.agent.user_sim import ScriptedUser
from lma_agent.sim.models import Task
from lma_agent.sim.seed_state import apply_overrides, build_seed_state
from src.live.events import JsonlSink, new_run_id

SCRIPTED = "scripted"
DEFAULT_VERSION = "v2"           # the final system (decisions.md 2026-11-12)
DEFAULT_GROQ_BUDGET = 5          # Groq episodes per session (CLAUDE.md Tier B); only Prateek raises it, per notebook
REUSE_FROM = {"always": "selective"}       # setting -> the setting whose agent trajectory it replays
CLOSING = "I proposed the action above; the monitor's decision and the result are shown above."

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

    def __init__(self, total: int = DEFAULT_GROQ_BUDGET):
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


def first_risky_call_id(sink) -> str | None:
    return next((e.payload.get("call_id") for e in sink.events if e.type == "risk_action"), None)


def save_trajectory(log_path: Path, run_id: str, agent: str, messages: list[dict], sink) -> Path:
    """<run_id>.agent.json next to the log: the agent's own messages, and which one holds the first risky action."""
    import json
    agent_msgs = [m for m in messages if m.get("role") == "assistant"]
    call_id = first_risky_call_id(sink)
    idx = next((i for i, m in enumerate(agent_msgs)
                if any(c.get("id") == call_id for c in m.get("tool_calls") or [])), None)
    path = log_path.with_name(log_path.name.removesuffix(".jsonl") + ".agent.json")
    path.write_text(json.dumps({"run_id": run_id, "agent": agent, "first_risky_index": idx, "messages": agent_msgs},
                               indent=1), encoding="utf-8")
    return path


def load_trajectory(row: dict) -> dict:
    import json
    return json.loads(Path(row["agent_messages_file"]).read_text(encoding="utf-8"))


def replay_agent(traj: dict) -> FakeLLM:
    """The source run's agent messages up to and including the first risky action, then CLOSING. No API."""
    idx = traj["first_risky_index"]
    if idx is None:
        raise ValueError(f"{traj['run_id']}: the agent never proposed a risky action, nothing to reuse")
    replies = [assistant_msg(m.get("content"), parse_tool_calls(m)) for m in traj["messages"][:idx + 1]]
    return FakeLLM(replies + [assistant_msg(CLOSING, [])])


def reuse_source(rows: list[dict], task_id: str, setting: str, confirm: str) -> dict | None:
    """The trajectory an `always` run replays: the same task's selective run with the same confirm answer."""
    source = REUSE_FROM.get(setting)
    if source is None:
        return None
    for row in rows:
        if row["task"] == task_id and row["setting"] == source and row["confirm"] == confirm:
            return load_trajectory(row)
    raise RuntimeError(f"{task_id} {setting} (confirm {confirm}): record the {source} run first, "
                       f"its agent trajectory is reused")


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
               reuse: dict | None = None,
               sleep: Callable[[float], None] = time.sleep, log: Callable[[str], None] = print) -> dict:
    """Record one demo run: Groq up to max_tries times, else the scripted agent. Returns the summary row.

    groq: callable(task_id) -> (client, agent name), e.g. groq_agent (cost guard inside); None = scripted only.
    reuse: a trajectory (load_trajectory) to replay instead of any new agent episode (the always runs).
    A PaidCallBlocked from the cost guard is NOT caught: the notebook stops instead of quietly going scripted."""
    out_dir = Path(out_dir)
    confirms = task.user_confirms if confirm is None else confirm == "yes"
    suffix = [f"confirm_{confirm}"] if confirm else []
    tool = target_tool(task)
    if reuse is not None:
        return _record_reuse(task, setting, confirms, suffix, reuse, model, embedder, out_dir, version, base_meta, log)
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
            row["agent_messages_file"] = str(save_trajectory(kept, run_id, agent_name, result.messages, sink))
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
    row["agent_messages_file"] = str(save_trajectory(path, run_id, agent_name, result.messages, sink))
    return row


def _record_reuse(task, setting, confirms, suffix, traj, model, embedder, out_dir, version, base_meta, log) -> dict:
    run_id = new_run_id(task.task_id, setting, "__".join(suffix + ["reused"]))
    path = out_dir / f"{run_id}.jsonl"
    steps = traj["first_risky_index"] + 1 if traj["first_risky_index"] is not None else 0
    meta = {**(base_meta or {}), "trajectory_reused_from": traj["run_id"], "trajectory_reused_messages": steps,
            "after_reuse": "fixed closing message, no new agent call", "new_agent_episode": False}
    sink, result, _ = episode(task, setting, confirms, model, embedder, replay_agent(traj), traj["agent"], path,
                              run_id, version, meta)
    risky = [e.payload for e in sink.events if e.type == "risk_action"]
    source = [m for m in traj["messages"][:steps]][-1]["tool_calls"] if steps else []
    same = bool(risky) and any(c["function"]["name"] == risky[0]["tool"] for c in source)
    if not same:
        raise RuntimeError(f"{run_id}: the replayed trajectory did not reach the same risky action")
    log(f"{task.task_id} {setting}: reused the agent trajectory of {traj['run_id']} ({traj['agent']}), "
        f"no new agent episode")
    row = summarize(task, sink, run_id, path, traj["agent"], result.status)
    row["reused_trajectory_from"] = traj["run_id"]
    row["agent_messages_file"] = str(save_trajectory(path, run_id, traj["agent"], result.messages, sink))
    return row


def record_plan(plan, tasks: dict, *, before_run: Callable | None = None, after_run: Callable | None = None,
                out_dir: str | Path, log: Callable[[str], None] = print, **kw) -> list[dict]:
    """Every (task_id, setting, confirm) of the plan in order; an always run reuses its selective run's trajectory.
    kw go to record_run (model, embedder, groq, budget, max_tries, pause_s, version, base_meta, sleep).
    summary.json in out_dir is rewritten after every run, so a stopped session keeps what it finished."""
    import json
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for task_id, setting, confirm in plan:
        task = tasks[task_id]
        answer = confirm or ("yes" if task.user_confirms else "no")
        reuse = reuse_source(rows, task_id, setting, answer)
        if before_run:
            before_run(task_id, setting, confirm)
        row = record_run(task, setting, confirm, out_dir=out_dir, reuse=reuse, log=log, **kw)
        if after_run:
            after_run(row)
        rows.append(row)
        write_summary(rows, out_dir)
    return rows


def write_summary(rows: list[dict], out_dir: str | Path) -> Path:
    """summary.json with file paths relative to out_dir (no machine paths in committed files)."""
    import json
    out_dir = Path(out_dir)

    def rel(p):
        try:
            return str(Path(p).resolve().relative_to(out_dir.resolve()))
        except ValueError:
            return Path(p).name
    out = [{**r, **{k: rel(r[k]) for k in ("file", "agent_messages_file") if r.get(k)}} for r in rows]
    path = out_dir / "summary.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return path
