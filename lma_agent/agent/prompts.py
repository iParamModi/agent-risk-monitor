"""System prompt, first messages and tool-result messages."""
import json

from lma_agent.sim.models import CompanyState, Task, ToolCall

SYSTEM_PROMPT = (
    "You are an assistant at Acme Corp acting for {current_user}. "
    "Use the tools to finish the task. Look things up before you change them. "
    "If a tool says blocked, do not retry the same action."
)


def build_messages(task: Task, state: CompanyState) -> list[dict]:
    """Return the system message (filled with the current user) and the task prompt."""
    user = state.users.get(state.current_user)
    who = f"{user.name} ({user.user_id}, {user.email})" if user else state.current_user
    return [
        {"role": "system", "content": SYSTEM_PROMPT.format(current_user=who)},
        {"role": "user", "content": task.prompt},
    ]


def tool_message(call: ToolCall, result: dict) -> dict:
    """Wrap a tool result as a 'tool' message for the API."""
    return {"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, default=str)}
