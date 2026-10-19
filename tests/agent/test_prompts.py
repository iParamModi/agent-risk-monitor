import json
from datetime import date

from lma_agent.agent.prompts import build_messages, tool_message
from lma_agent.sim.models import Task, ToolCall
from lma_agent.sim.seed_state import build_seed_state


def test_build_messages():
    msgs = build_messages(Task(task_id="t", domain="FILE", prompt="Delete old reports."), build_seed_state(0))
    assert [m["role"] for m in msgs] == ["system", "user"]
    assert "Riya Sharma (u_riya" in msgs[0]["content"] and "blocked" in msgs[0]["content"]
    assert msgs[1]["content"] == "Delete old reports."


def test_tool_message():
    m = tool_message(ToolCall(id="c9", name="x", args={}), {"modified": date(2024, 3, 2), "ok": 1})
    assert m["role"] == "tool" and m["tool_call_id"] == "c9"
    assert json.loads(m["content"]) == {"modified": "2024-03-02", "ok": 1}
