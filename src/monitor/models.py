"""Model clients for the monitor: one OpenAI-compatible client (vLLM for Qwen3-8B, a hosted API for
Qwen3-235B-A22B, PLAN Step 15.4) and a FakeModel for tests.

Decoding is fixed by R9.7: temperature 0, at most 512 new tokens, Qwen3 thinking off.
"""
import time
from dataclasses import dataclass

TEMPERATURE = 0.0
MAX_NEW_TOKENS = 512
BACKOFF_SECONDS = [2, 4, 8, 16]


@dataclass
class Generation:
    text: str
    tokens_in: int | None = None
    tokens_out: int | None = None


class OpenAICompatModel:
    """Chat model behind an OpenAI-compatible endpoint.

    thinking_off: "template" sends chat_template_kwargs.enable_thinking=False (vLLM serving Qwen3);
                  "none" sends nothing (models that never think, e.g. Qwen3-...-Instruct-2507).
    """

    def __init__(self, model: str, base_url: str, api_key: str, thinking_off: str = "template"):
        from openai import OpenAI
        self.name = model
        self.thinking_off = thinking_off
        self.client = OpenAI(base_url=base_url, api_key=api_key or "EMPTY", max_retries=0)

    def generate(self, messages: list[dict]) -> Generation:
        from openai import APIConnectionError, InternalServerError, RateLimitError
        extra = {"chat_template_kwargs": {"enable_thinking": False}} if self.thinking_off == "template" else None
        for attempt, wait in enumerate(BACKOFF_SECONDS + [None]):
            try:
                resp = self.client.chat.completions.create(
                    model=self.name, messages=messages, temperature=TEMPERATURE,
                    max_tokens=MAX_NEW_TOKENS, extra_body=extra)
                break
            except (RateLimitError, APIConnectionError, InternalServerError):
                if wait is None:
                    raise
                time.sleep(wait)
        usage = resp.usage
        return Generation(resp.choices[0].message.content or "",
                          usage.prompt_tokens if usage else None,
                          usage.completion_tokens if usage else None)


class FakeModel:
    """Returns scripted answers in order; records the prompts it saw (tests, dry runs)."""

    name = "fake"

    def __init__(self, answers: list[str]):
        self.answers = list(answers)
        self.prompts: list[list[dict]] = []

    def generate(self, messages: list[dict]) -> Generation:
        self.prompts.append(messages)
        text = self.answers.pop(0) if self.answers else ""
        return Generation(text, sum(len(m["content"].split()) for m in messages), len(text.split()))
