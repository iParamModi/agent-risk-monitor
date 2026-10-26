"""src/training/build_sft.py and the tokenizing in train_lora.py (no GPU needed)."""
import json

import pytest

from src.monitor.parser import parse_output
from src.training.build_sft import example, risk_target
from src.training.train_lora import Collator, tokenize


def rec(label="UNSAFE", rtype="FINANCIAL_LOSS"):
    return {"record_id": "AR-001", "source": "agentrisk",
            "visible": {"trajectory": [{"role": "user", "text": "Pay it.", "tool_call": None, "action_text": None}],
                        "proposed_action": None, "proposed_action_text": "payments.submit --amount 9"},
            "gold": {"risk_label": label, "risk_type": rtype, "risk_cause": "SECRET_CAUSE", "source_note": "SECRET_NOTE"}}


def test_target_is_a_valid_risk_answer():
    for label, rtype in (("UNSAFE", "FINANCIAL_LOSS"), ("SAFE", "NONE")):
        assert parse_output(risk_target({"risk_label": label, "risk_type": rtype}), ("RISK",)) == \
            {"type": "RISK", "risk_label": label, "risk_type": rtype}
    with pytest.raises(ValueError):
        risk_target({"risk_label": "UNSAFE", "risk_type": None})


def test_example_uses_the_monitor_prompt_and_no_gold_text():
    ex = example(rec())
    prompt = ex["messages"][0]["content"]
    assert "PROPOSED NEXT ACTION (not yet executed): payments.submit --amount 9" in prompt
    assert "SECRET" not in prompt and "FINANCIAL_LOSS\"" not in prompt.split("## Examples")[0]
    assert json.loads(ex["target"])["risk_type"] == "FINANCIAL_LOSS"


class FakeTokenizer:
    def apply_chat_template(self, messages, tokenize, add_generation_prompt, enable_thinking):
        assert add_generation_prompt and not enable_thinking and not tokenize
        return "PROMPT " + messages[0]["content"]

    def __call__(self, text, add_special_tokens):
        assert not add_special_tokens
        if text.startswith("PROMPT "):
            return {"input_ids": [1] * len(text.split()[1:])}
        return {"input_ids": [7] * len(text.split())}


def test_loss_only_on_target_and_long_examples_dropped():
    ex = {"messages": [{"role": "user", "content": "a b c"}], "target": "x y"}
    t = tokenize(ex, FakeTokenizer(), max_len=10)
    assert t["input_ids"] == [1, 1, 1, 7, 7] and t["labels"] == [-100, -100, -100, 7, 7]
    assert tokenize(ex, FakeTokenizer(), max_len=4) is None
    batch = Collator(pad_id=0)([t, {"input_ids": [5], "labels": [5]}])
    assert batch["labels"][1].tolist() == [5, -100, -100, -100, -100]
    assert batch["attention_mask"][1].tolist() == [1, 0, 0, 0, 0]
