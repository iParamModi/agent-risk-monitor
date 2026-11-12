"""A record for run_monitor built from a live agent run: VISIBLE input only.

record_from_live(task, messages, call) turns the agent's chat messages (OpenAI format, as lma_agent keeps them)
and its proposed write into the record shape of data/records (visible.trajectory + visible.proposed_action).
There is no hidden state, no gold and no policy logic in it: the monitor learns facts only through the gateway
(src.gateway.gateway.for_state over the live company state).
"""
import json

from lma_agent.sim.models import Task, ToolCall


def _text(content) -> str:
    if content is None:
        return ""
    return content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)


def trajectory_from_messages(messages: list[dict], stop_call_id: str | None = None) -> list[dict]:
    """user -> USER, assistant -> AGENT (one entry per tool call), tool -> TOOL; the system prompt is left out.
    Stops before the tool call with id stop_call_id (the proposed action is not part of the trajectory)."""
    out = []

    def entry(role, text="", tool_call=None):
        return {"role": role, "text": text, "tool_call": tool_call, "action_text": None}

    for msg in messages:
        role = msg.get("role")
        if role == "user":
            out.append(entry("user", _text(msg.get("content"))))
        elif role == "assistant":
            text = _text(msg.get("content")).strip()
            calls = msg.get("tool_calls") or []
            if not calls:
                if text:
                    out.append(entry("agent", text))
                continue
            for i, tc in enumerate(calls):
                if tc.get("id") == stop_call_id:
                    if i == 0 and text:
                        out.append(entry("agent", text))
                    return out
                fn = tc.get("function") or {}
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {"_raw": fn.get("arguments")}
                out.append(entry("agent", text if i == 0 else "", {"name": fn.get("name"), "args": args}))
        elif role == "tool":
            out.append(entry("tool", _text(msg.get("content"))))
    return out


def record_from_live(task: Task, messages: list[dict], call: ToolCall, record_id: str | None = None) -> dict:
    """The record run_monitor needs (task decide_action), with only what the agent's conversation shows."""
    return {
        "record_id": record_id or f"live-{task.task_id}-{call.id}",
        "seed_id": None, "source": "live", "set": "live", "split": None, "domain": task.domain,
        "case_type": None, "subtype": None, "pair_side": None, "version": None, "task": "decide_action",
        "visible": {"trajectory": trajectory_from_messages(messages, stop_call_id=call.id),
                    "proposed_action": {"name": call.name, "args": dict(call.args)}},
    }
