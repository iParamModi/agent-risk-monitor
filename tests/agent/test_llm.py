from types import SimpleNamespace

import pytest
from openai import BadRequestError, RateLimitError

from lma_agent.agent import llm
from lma_agent.agent.llm import FakeLLM, assistant_msg, call_llm, parse_tool_calls
from lma_agent.sim.models import ToolCall
from lma_agent.tools.registry import get_agent_tool_schemas

def http_response(status, headers=None):
    """Minimal stand-in for the SDK's HTTP response (only what the error classes read)."""
    return SimpleNamespace(status_code=status, headers=headers or {}, request=None)


def api_message(content=None, calls=()):
    tcs = [SimpleNamespace(id=i, type="function", function=SimpleNamespace(name=n, arguments=a))
           for i, n, a in calls]
    return SimpleNamespace(content=content, tool_calls=tcs or None)


def api_response(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class ScriptedClient:
    """Fake OpenAI client: each create() pops the next item; exceptions are raised."""

    def __init__(self, items):
        self.items, self.kwargs = list(items), []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.kwargs.append(kwargs)
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def rate_limit(headers=None):
    return RateLimitError("slow down", response=http_response(429, headers), body=None)


def bad_request(text):
    return BadRequestError(text, response=http_response(400), body=None)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    waits = []
    monkeypatch.setattr(llm.time, "sleep", waits.append)
    monkeypatch.setattr(llm, "_use_parallel_flag", True)
    return waits


def test_parse_tool_calls():
    msg = api_message(calls=[("c1", "read_file", '{"path": "/a"}'), ("c2", "read_inbox", "null"),
                             ("c3", "delete_file", '{"path": "/a"'), ("c4", "x", "[1]")])
    calls = parse_tool_calls(msg)
    assert calls[0] == ToolCall(id="c1", name="read_file", args={"path": "/a"})
    assert calls[1].args == {}
    assert calls[2].args == {"_raw": '{"path": "/a"'}
    assert calls[3].args == {"_raw": "[1]"}
    assert parse_tool_calls(api_message("hi")) == []


def test_assistant_msg_raw_round_trips():
    m = assistant_msg(None, [ToolCall(id="c1", name="read_file", args={"path": "/a"})])
    assert m.raw["tool_calls"][0]["function"] == {"name": "read_file", "arguments": '{"path": "/a"}'}
    assert parse_tool_calls(m.raw) == m.tool_calls
    assert "tool_calls" not in assistant_msg("done", []).raw


def test_call_llm_passes_settings():
    client = ScriptedClient([api_response(api_message("ok"))])
    out = call_llm(client, [{"role": "user", "content": "hi"}], [])
    kw = client.kwargs[0]
    assert out.content == "ok" and out.tool_calls == []
    assert kw["model"] == "openai/gpt-oss-120b" and kw["temperature"] == 0.0
    assert kw["tool_choice"] == "auto" and kw["parallel_tool_calls"] is False


def test_retry_on_429_uses_header_then_backoff(no_sleep):
    client = ScriptedClient([rate_limit({"retry-after": "5"}), rate_limit({"retry-after": "1.5"}), rate_limit(),
                             api_response(api_message("ok"))])
    assert call_llm(client, [], []).content == "ok"
    assert no_sleep == [5, 4, 8]  # header when longer, else the backoff


def test_429_gives_up_after_max_retries():
    client = ScriptedClient([rate_limit()] * 4)
    with pytest.raises(RateLimitError):
        call_llm(client, [], [])


def test_retry_on_tool_use_failed():
    client = ScriptedClient([bad_request("tool_use_failed: bad json"), api_response(api_message("ok"))])
    assert call_llm(client, [], []).content == "ok"


def test_parallel_flag_dropped_if_rejected():
    client = ScriptedClient([bad_request("unsupported parameter parallel_tool_calls"), api_response(api_message("ok"))])
    assert call_llm(client, [], []).content == "ok"
    assert "parallel_tool_calls" not in client.kwargs[1]


def test_other_bad_request_raises():
    with pytest.raises(BadRequestError):
        call_llm(ScriptedClient([bad_request("invalid model")]), [], [])


def test_fake_llm():
    a, b = assistant_msg("one", []), assistant_msg("two", [])
    fake = FakeLLM([a, b])
    assert call_llm(fake, [{"role": "user", "content": "x"}], []) is a
    assert call_llm(fake, [], []) is b
    assert fake.received[0] == [{"role": "user", "content": "x"}]
    with pytest.raises(RuntimeError):
        call_llm(fake, [], [])
    assert call_llm(FakeLLM([a], repeat_last=True), [], []) is a


@pytest.mark.live
def test_live_groq_returns_parsed_tool_call():
    tools = [s for s in get_agent_tool_schemas() if s["function"]["name"] in ("get_file_info", "delete_file")]
    messages = [{"role": "system", "content": "You are an assistant at Acme Corp. Use the tools."},
                {"role": "user", "content": "Who owns /project/report_7.pdf?"}]
    out = call_llm(llm.make_client(), messages, tools)
    assert out.tool_calls and out.tool_calls[0].name == "get_file_info"
    assert out.tool_calls[0].args == {"file": "/project/report_7.pdf"}
