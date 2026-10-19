"""The agent loop: the only module that knows the order of things."""
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


def run_agent(task: Task, state: CompanyState, client, gate: Gate = allow_all, user: ScriptedUser | None = None,
              max_steps: int = MAX_STEPS, out_dir: str | Path | None = None) -> EpisodeResult:
    """Run one episode until the model stops, a write is escalated, or max_steps is hit."""
    user = user or ScriptedUser(task.user_confirms)
    episode_id = new_episode_id(task.task_id)
    messages = build_messages(task, state)
    schemas = get_agent_tool_schemas(phase=1, include_ood=task.domain == "CUST")
    steps: list[StepLog] = []
    errors, llm_calls = 0, 0

    def finish(status: str, answer: str | None) -> EpisodeResult:
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
            return finish("error", f"llm_error: {type(err).__name__}: {err}")
        llm_calls += 1
        messages.append(msg.raw)
        if not msg.tool_calls:
            return finish("done", msg.content)
        for call in msg.tool_calls:
            state, result, log, stop = handle_call(state, call, messages, gate, user, episode_id, step)
            steps.append(log)
            errors += "error" in result
            messages.append(tool_message(call, result))
            if stop:
                return finish("escalated", None)
    return finish("max_steps", None)


def handle_call(state: CompanyState, call: ToolCall, messages: list[dict], gate: Gate, user: ScriptedUser,
                episode_id: str = "", step: int = 0) -> tuple[CompanyState, dict, StepLog, bool]:
    """Validate one call, run it (reads directly, writes through the gate) and log it."""
    before = state_hash(state)

    def log(tool_type: str, decision: str | None, executed: bool, result: dict) -> StepLog:
        return make_step_log(episode_id, step, messages, call, tool_type, decision, before, executed, result)

    err = validate_call(call, SPECS)
    if err:
        return state, err, log("invalid", None, False, err), False
    if call.name in READ_TOOLS:
        result = run_read(state, call)
        return state, result, log("read", None, True, result), False

    d = gate(messages, call)
    if d.decision == "ALLOW" or (d.decision == "ASK_CONFIRMATION" and user.confirm(call)):
        state, result = apply_action(state, call)
        executed = "error" not in result
    elif d.decision == "ASK_CONFIRMATION":
        result, executed = {"status": "declined_by_user"}, False
    elif d.decision == "BLOCK":
        result, executed = {"status": "blocked", "policy": d.policy_id, "reason": d.reason}, False
    else:
        result, executed = {"status": "escalated_to_human"}, False
    return state, result, log("write", d.decision, executed, result), d.decision == "ESCALATE"
