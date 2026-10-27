"""Model clients for the monitor: one OpenAI-compatible client (vLLM for Qwen3-8B, a hosted API for
Qwen3-235B-A22B, PLAN Step 15.4), a local Hugging Face model (Kaggle GPU; base or + LoRA adapter, so the
base and fine-tuned runs use the same code and precision) and a FakeModel for tests.

Decoding is fixed by R9.7: temperature 0, at most 512 new tokens, Qwen3 thinking off.
"""
import time
from dataclasses import dataclass

TEMPERATURE = 0.0
MAX_NEW_TOKENS = 512
PREFILL_CHUNK = 1024    # transformers backend: longer prompts fill the KV cache in pieces of this many tokens
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


class TransformersModel:
    """Hugging Face model on local GPUs (e.g. Kaggle 2x T4): float16, spread over the GPUs, greedy decoding.

    adapter: a LoRA adapter (folder or Hub id) loaded on top of the base model (Step 17 fine-tuned run).
    Prompts longer than PREFILL_CHUNK are read in pieces: a T4 has no flash attention, so one pass over a
    7k-token prompt builds the full attention matrix (several GB) and runs out of memory. Same answers.
    """

    def __init__(self, model: str, revision: str | None = None, adapter: str | None = None, dtype: str = "float16"):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import time
        from collections import Counter
        start = time.perf_counter()
        self.name = f"{model}+{adapter}" if adapter else model
        self.tokenizer = AutoTokenizer.from_pretrained(model, revision=revision)
        self.model = AutoModelForCausalLM.from_pretrained(model, revision=revision, dtype=getattr(torch, dtype),
                                                          device_map="auto")
        if adapter:
            from peft import PeftModel
            self.model = PeftModel.from_pretrained(self.model, adapter)
        self.model.eval()
        # layers on 'cpu' or 'disk' mean the model did not fit on the GPUs (very slow generation)
        where = Counter(str(d) for d in (getattr(self.model, "hf_device_map", None) or {}).values())
        print(f"[run] model loaded in {time.perf_counter() - start:.0f}s | layers per device {dict(where)}", flush=True)

    def generate(self, messages: list[dict]) -> Generation:
        import torch
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True,
                                                  enable_thinking=False)
        inputs = self.tokenizer(text, return_tensors="pt", add_special_tokens=False).to(self.model.device)
        ids, cache = inputs["input_ids"], None
        with torch.no_grad():   # temperature 0 = greedy; unset the sampling defaults of generation_config.json
            if ids.shape[1] > PREFILL_CHUNK:    # all but the last token; generate() then starts from the cache
                from transformers import DynamicCache
                cache = DynamicCache(config=self.model.config)
                for s in range(0, ids.shape[1] - 1, PREFILL_CHUNK):
                    self.model(input_ids=ids[:, s:min(s + PREFILL_CHUNK, ids.shape[1] - 1)], past_key_values=cache,
                               use_cache=True, logits_to_keep=1)
            out = self.model.generate(**inputs, past_key_values=cache, max_new_tokens=MAX_NEW_TOKENS, do_sample=False,
                                      temperature=None, top_p=None, top_k=None)
        new = out[0, inputs["input_ids"].shape[1]:]
        return Generation(self.tokenizer.decode(new, skip_special_tokens=True), inputs["input_ids"].shape[1], len(new))


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
