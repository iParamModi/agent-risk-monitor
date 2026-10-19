"""Groq client (OpenAI-compatible), call_llm with retries, tool-call parsing and a FakeLLM for tests."""
import copy
import json
import time

from openai import BadRequestError, OpenAI, RateLimitError

from lma_agent.config import BASE_URL, GROQ_API_KEY, MAX_RETRIES, MODEL, TEMPERATURE
from lma_agent.sim.models import AssistantMsg, ToolCall

BACKOFF_SECONDS = [2, 4, 8]
_use_parallel_flag = True  # turned off once if the API rejects parallel_tool_calls


def make_client() -> OpenAI:
    """Return an OpenAI SDK client pointed at Groq; call_llm does the retrying."""
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set (add it to .env)")
    return OpenAI(base_url=BASE_URL, api_key=GROQ_API_KEY, max_retries=0)


def _get(obj, key):
    """Read a field from an SDK object or a dict."""
    return obj.get(key) if isinstance(obj, dict) else getattr(obj, key, None)


def _parse_args(text: str | None) -> dict:
    """Parse a tool-call arguments string; anything that isn't a JSON object becomes {"_raw": text}."""
    if text in (None, "", "null"):
        return {}
    try:
        args = json.loads(text)
    except json.JSONDecodeError:
        return {"_raw": text}
    return args if isinstance(args, dict) else {"_raw": text}


def parse_tool_calls(raw_msg) -> list[ToolCall]:
    """Turn the API message's tool calls into ToolCall objects."""
    calls = []
    for tc in _get(raw_msg, "tool_calls") or []:
        fn = _get(tc, "function")
        calls.append(ToolCall(id=_get(tc, "id"), name=_get(fn, "name"), args=_parse_args(_get(fn, "arguments"))))
    return calls


def assistant_msg(content: str | None, tool_calls: list[ToolCall]) -> AssistantMsg:
    """Build an AssistantMsg whose `raw` is a valid assistant message to send back to the API."""
    raw: dict = {"role": "assistant", "content": content}
    if tool_calls:
        raw["tool_calls"] = [
            {"id": c.id, "type": "function",
             "function": {"name": c.name,
                          "arguments": c.args["_raw"] if set(c.args) == {"_raw"} else json.dumps(c.args)}}
            for c in tool_calls
        ]
    return AssistantMsg(content=content, tool_calls=tool_calls, raw=raw)


def _retry_wait(err: RateLimitError, attempt: int) -> float:
    """Seconds to wait after a 429: the retry-after header if present, else 2s, 4s, 8s."""
    header = err.response.headers.get("retry-after") if err.response is not None else None
    try:
        return float(header)
    except (TypeError, ValueError):
        return BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]


def call_llm(client, messages: list[dict], tools: list[dict]) -> AssistantMsg:
    """Ask the model for its next message; retries on 429 and on Groq's broken tool-call error."""
    global _use_parallel_flag
    if isinstance(client, FakeLLM):
        return client.reply(messages, tools)
    for attempt in range(MAX_RETRIES + 1):
        extra = {"parallel_tool_calls": False} if _use_parallel_flag else {}
        try:
            resp = client.chat.completions.create(model=MODEL, messages=messages, tools=tools,
                                                  tool_choice="auto", temperature=TEMPERATURE, **extra)
            msg = resp.choices[0].message
            return assistant_msg(msg.content, parse_tool_calls(msg))
        except RateLimitError as err:
            if attempt == MAX_RETRIES:
                raise
            time.sleep(_retry_wait(err, attempt))
        except BadRequestError as err:
            text = str(err)
            if "parallel_tool_calls" in text and _use_parallel_flag:
                _use_parallel_flag = False
                continue
            if "tool_use_failed" in text and attempt < MAX_RETRIES:
                continue
            raise
    raise RuntimeError("call_llm: retries exhausted")


class FakeLLM:
    """Scripted stand-in for the Groq client: returns `replies` in order and records what it was sent."""

    def __init__(self, replies: list[AssistantMsg], repeat_last: bool = False):
        self.replies = list(replies)
        self.repeat_last = repeat_last
        self.received: list[list[dict]] = []
        self.calls = 0

    def reply(self, messages: list[dict], tools: list[dict]) -> AssistantMsg:
        """Return the next scripted reply."""
        self.received.append(copy.deepcopy(messages))
        if self.calls < len(self.replies):
            msg = self.replies[self.calls]
        elif self.repeat_last and self.replies:
            msg = self.replies[-1]
        else:
            raise RuntimeError("FakeLLM ran out of replies")
        self.calls += 1
        return msg
