"""The agent loop: the only module that knows the order of things.

on_event (optional): called with one src.live.events.Event per thing that happens (company_snapshot first: the full
initial state for the human viewer, never given to the gate; then instruction, tool_call,
observation, risk_action, the gate's own events, confirm_request/answer, action_applied/refused, state_diff,
final_response). None = no events (the default; scripts/run_live.py passes a JsonlSink).

A gate with an `observe(state=, emit=, step=)` method (src.live.monitor_gate.MonitorGate) is told the live company
state before each write it judges, and emits its own policies / monitor / gateway_check / decision events.
"""
from collections.abc import Callable
from pathlib import Path

from lma_agent.agent.gate import Gate, allow_all
from lma_agent.agent.llm import call_llm
from lma_agent.agent.logger import make_step_log, new_episode_id, save_episode
from lma_agent.agent.prompts import build_messages, tool_message
from lma_agent.agent.user_sim import ScriptedUser
from lma_agent.config import MAX_STEPS
from lma_agent.sim.models import CompanyState, EpisodeResult, StepLog, Task, ToolCall
from lma_agent.sim.seed_state import state_hash
from lma_agent.tools.read_tools import run_read
from lma_agent.tools.registry import READ_TOOLS, SPECS, get_agent_tool_schemas
from lma_agent.tools.validate import validate_call
from lma_agent.tools.write_tools import apply_action

Emit = Callable[[str, dict], None]     # emit(type, payload) for the current step


def _no_emit(type: str, payload: dict) -> None:
    pass


def run_agent(task: Task, state: CompanyState, client, gate: Gate = allow_all, user: ScriptedUser | None = None,
              max_steps: int = MAX_STEPS, out_dir: str | Path | None = None, on_event=None,
              run_id: str | None = None, meta: dict | None = None) -> EpisodeResult:
    """Run one episode until the model stops, a write is escalated, or max_steps is hit."""
    user = user or ScriptedUser(task.user_confirms)
    episode_id = new_episode_id(task.task_id)
    run_id = run_id or episode_id
    messages = build_messages(task, state)
    schemas = get_agent_tool_schemas(phase=1, include_ood=task.domain == "CUST")
    steps: list[StepLog] = []
    errors, llm_calls = 0, 0

    def emitter(step: int) -> Emit:
        if on_event is None:
            return _no_emit
        from src.live.events import make_event

        def emit(type: str, payload: dict) -> None:
            on_event(make_event(run_id, step, type, payload))
        return emit

    if on_event is not None:
        from src.live.company import company_snapshot
        emitter(0)("company_snapshot", company_snapshot(task, state))
    emitter(0)("instruction", {"task_id": task.task_id, "prompt": task.prompt, "current_user": state.current_user,
                              "meta": meta or {}})

    def finish(status: str, answer: str | None, step: int) -> EpisodeResult:
        emitter(step)("final_response", {"status": status, "text": answer})
        result = EpisodeResult(episode_id=episode_id, task_id=task.task_id, status=status, final_answer=answer,
                               messages=messages, steps=steps, n_llm_calls=llm_calls, n_tool_errors=errors,
                               final_state_hash=state_hash(state))
        if out_dir is not None:
            save_episode(result, out_dir)
        return result

    for step in range(1, max_steps + 1):
        try:
            msg = call_llm(client, messages, schemas)
        except Exception as err:  # API down, retries exhausted, FakeLLM out of replies
            return finish("error", f"llm_error: {type(err).__name__}: {err}", step)
        llm_calls += 1
        messages.append(msg.raw)
        if not msg.tool_calls:
            return finish("done", msg.content, step)
        for call in msg.tool_calls:
            state, result, log, stop = handle_call(state, call, messages, gate, user, episode_id, step,
                                                   emit=emitter(step), list_shows_sharing=task.list_shows_sharing)
            steps.append(log)
            errors += "error" in result
            messages.append(tool_message(call, result))
            if stop:
                return finish("escalated", None, step)
    return finish("max_steps", None, max_steps)


def handle_call(state: CompanyState, call: ToolCall, messages: list[dict], gate: Gate, user: ScriptedUser,
                episode_id: str = "", step: int = 0, emit: Emit = _no_emit,
                list_shows_sharing: bool = False) -> tuple[CompanyState, dict, StepLog, bool]:
    """Validate one call, run it (reads directly, writes through the gate) and log it."""
    before = state_hash(state)

    def log(tool_type: str, decision: str | None, executed: bool, result: dict) -> StepLog:
        return make_step_log(episode_id, step, messages, call, tool_type, decision, before, executed, result)

    err = validate_call(call, SPECS)
    if err:
        emit("tool_call", {"tool": call.name, "args": call.args, "call_id": call.id})
        emit("observation", {"tool": call.name, "result": err})
        return state, err, log("invalid", None, False, err), False
    if call.name in READ_TOOLS:
        emit("tool_call", {"tool": call.name, "args": call.args, "call_id": call.id})
        result = run_read(state, call, list_shows_sharing=list_shows_sharing)
        emit("observation", {"tool": call.name, "result": result})
        return state, result, log("read", None, True, result), False

    emit("risk_action", {"tool": call.name, "args": call.args, "call_id": call.id})
    observe = getattr(gate, "observe", None)
    if observe is not None:
        observe(state=state, emit=emit, step=step)
    d = gate(messages, call)
    if observe is None:      # simple gates (allow_all, fake_gate): the loop logs their decision
        emit("decision", {"decision": d.decision, "policy_ids": [d.policy_id] if d.policy_id else [],
                          "reason": d.reason, "checks_used": 0, "checks_always": None})

    confirmed = None
    if d.decision == "ASK_CONFIRMATION":
        emit("confirm_request", {"tool": call.name, "args": call.args, "policy_id": d.policy_id, "reason": d.reason})
        confirmed = user.confirm(call)
        emit("confirm_answer", {"answer": "yes" if confirmed else "no"})

    old_state = state
    if d.decision == "ALLOW" or confirmed:
        state, result = apply_action(state, call)
        executed = "error" not in result
    elif d.decision == "ASK_CONFIRMATION":
        result, executed = {"status": "declined_by_user", "decision": d.decision, "policy": d.policy_id}, False
    elif d.decision == "BLOCK":
        result, executed = {"status": "blocked", "decision": d.decision, "policy": d.policy_id, "reason": d.reason}, False
    else:
        result, executed = {"status": "escalated_to_human", "decision": d.decision, "policy": d.policy_id}, False

    if executed:
        emit("action_applied", {"tool": call.name, "args": call.args, "result": result})
    else:
        emit("action_refused", {"tool": call.name, "args": call.args, "decision": d.decision,
                                "policy_id": d.policy_id, "result": result})
    if emit is not _no_emit:
        from src.live.events import state_diff
        emit("state_diff", state_diff(old_state, state))
    return state, result, log("write", d.decision, executed, result), d.decision == "ESCALATE"
