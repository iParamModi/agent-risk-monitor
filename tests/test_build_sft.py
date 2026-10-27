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


# ---------------------------------------------------------------- Phase B: (a) and (b) from our records

POLICIES = [{"policy_id": f"P_FILE_{i:02d}", "text": f"Rule number {i} about files."} for i in range(1, 7)]


class FakeRetriever:
    """Ranks policies by id, so the look-alikes are known."""

    def search(self, query, k):
        return POLICIES[:k]


class FakeGateway:
    def __init__(self, record):
        self.facts = record["hidden"]["key_facts"]

    def call(self, tool, args):
        if tool != "check_file_sharing":
            return {"error": "unknown_tool"}
        return {"path": args["path"], "sharing": self.facts["memo.pdf.sharing"], "shared_external": True}


TOOLS = [{"name": "check_file_sharing", "args": {"path": "File or folder path"}, "returns": "{sharing: string}"}]


def our_record(rid="IND-FILE-T2-901-c", check=True, split="train", **gold):
    g = {"decision": "BLOCK", "risk_label": "UNSAFE", "risk_type": "PRIVACY_LEAKAGE", "risk_cause": "ENVIRONMENT_STATE",
         "check_needed": check, "missing_fact": "sharing of memo.pdf" if check else None,
         "required_checks": [{"tool": "check_file_sharing", "args": {"path": "memo.pdf"}}] if check else None,
         "policy_ids": ["P_FILE_04"], "evidence": {"facts": ["memo.pdf sharing = external:org_4"],
                                                   "policy_ids": ["P_FILE_04"]}}
    g.update(gold)
    return {"record_id": rid, "seed_id": rid.rsplit("-", 1)[0], "source": "synthetic-data", "set": "in_domain",
            "split": split, "case_type": rid.split("-")[2], "subtype": rid.rsplit("-", 1)[1] if "-T2-" in rid else None,
            "visible": {"trajectory": [{"role": "user", "text": "Move memo.pdf, then share it.", "tool_call": None,
                                        "action_text": None}],
                        "proposed_action": {"name": "share_file", "args": {"file": "memo.pdf", "with": "bo"}}},
            "hidden": {"state": {"SECRET_STATE": 1}, "key_facts": {"memo.pdf.sharing": "external:org_4"}}, "gold": g}


def phase_b(train, val=(), gateway=FakeGateway):
    from src.training.build_sft import build_phase_b
    return build_phase_b(list(train), list(val), ([{"source": "atbench", "kind": "risk", "target": "R"}], []),
                         POLICIES, FakeRetriever(), TOOLS, gateway)


def test_phase_b_first_and_second_pass_targets():
    train, val, stats = phase_b([our_record()])
    first, second = train[0], train[1]
    assert (first["kind"], second["kind"]) == ("first_pass", "second_pass")
    need = parse_output(first["target"], ("DECISION", "NEED_INFORMATION"))
    assert need["type"] == "NEED_INFORMATION" and need["missing_fact"] == "sharing of memo.pdf"
    assert need["checks"] == [{"tool": "check_file_sharing", "args": {"path": "memo.pdf"}}]
    decision = parse_output(second["target"], ("DECISION",))
    assert decision["decision"] == "BLOCK" and decision["evidence"]["facts"] == ["memo.pdf sharing = external:org_4"]
    # the prompt shows the gold policy among 3 under a number, and the target cites that number
    prompt = second["messages"][0]["content"]
    ref = decision["evidence"]["policy_ids"][0]
    assert f"- [{ref}] Rule number 4 about files." in prompt and prompt.count("- [") == 3
    assert '"sharing": "external:org_4"' in prompt and "NEED_INFORMATION" not in prompt      # second pass decides
    assert "Check tools (read-only)" in first["messages"][0]["content"]
    assert "SECRET_STATE" not in json.dumps(train) and "P_FILE" not in json.dumps([e for e in train if "messages" in e])
    # x2 on train, then the external examples; once on val
    assert [e["kind"] for e in train] == ["first_pass", "second_pass"] * 2 + ["risk"]
    assert stats["train"]["by_kind"] == {"first_pass": 2, "second_pass": 2, "risk": 1}


def test_phase_b_no_check_case_is_one_decision():
    rec = our_record("IND-FILE-T3-901-v1", check=False, decision="ALLOW", risk_label="SAFE", risk_type="NONE",
                     risk_cause="NONE", evidence={"facts": ["memo.pdf owner = user_5"], "policy_ids": ["P_FILE_04"]})
    train, _, _ = phase_b([rec])
    assert [e["kind"] for e in train] == ["first_pass", "first_pass", "risk"]
    assert parse_output(train[0]["target"], ("DECISION",))["decision"] == "ALLOW"


def test_phase_b_refuses_until_checks_and_gateway_exist():
    from src.training.build_sft import NotReady
    with pytest.raises(NotReady, match="required_checks"):
        phase_b([our_record(required_checks=None)])
    with pytest.raises(NotReady, match="gateway"):
        phase_b([our_record()], gateway=None)
    with pytest.raises(NotReady, match="does not have"):
        phase_b([our_record(required_checks=[{"tool": "check_legal_hold", "args": {"file": "memo.pdf"}}])])


def test_phase_b_gold_check_that_fails_stops_the_build():
    with pytest.raises(ValueError, match="fails"):
        phase_b([our_record()], gateway=lambda r: type("G", (), {"call": lambda self, t, a: {"error": "not_found"}})())


def test_phase1_keeps_only_phase1_records_of_the_split():
    from src.training.build_sft import phase1
    event = our_record("IND-CAL-T3-901-v1", check=False)
    event["visible"]["proposed_action"] = {"name": "create_event", "args": {}}
    assert [r["record_id"] for r in phase1([our_record(), event], "train")] == ["IND-FILE-T2-901-c"]
    with pytest.raises(ValueError):
        phase1([our_record(split="test")], "train")


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
    batch = Collator(pad_id=0)([t, {"input_ids": [5, 6], "labels": [-100, 6]}])
    assert batch["input_ids"][1].tolist() == [5, 6, 0, 0, 0]
    assert batch["attention_mask"][1].tolist() == [1, 1, 0, 0, 0]
    # logits only from one token before the earliest target (row 2: index 1), labels cut the same way
    assert batch["logits_to_keep"] == 5 and batch["labels"].tolist() == [[-100, -100, -100, 7, 7], [-100, 6, -100, -100, -100]]
    one = Collator(pad_id=0)([t])
    assert one["logits_to_keep"] == 3 and one["labels"].tolist() == [[-100, 7, 7]]
