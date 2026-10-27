"""Makes the SFT files (PLAN Step 16, DATASET.md section 8).

    python -m src.training.build_sft                 Phase A -> data/training/sft_train.jsonl, sft_val.jsonl, stats.json
    python -m src.training.build_sft --phase b       Phase B -> sft_train.jsonl, sft_val.jsonl, stats_phase_b.json

Phase A has only kind (c), risk examples from the external records:
- train: the records in data/external/splits/phase_a_train.txt (src.external.phase_a); val: every external
  val record
- input: exactly the monitor's prompt (prompt_builder.build_risk_prompt, as chat messages), so training and
  inference see the same text
- target: built by code from the gold fields (never by an LLM), in the parser's RISK format

Phase B adds kinds (a) and (b) from our own records, then the same (c):
- records: data/records/train.jsonl (val: val.jsonl), phase 1 tools only (configs/tool_phases.yaml); test and
  OOD records are never read
- (a) first pass: the selective first-pass prompt (check tools listed, NEED_INFORMATION allowed) -> DECISION
  when no check is needed, else NEED_INFORMATION with the gold missing_fact and required_checks and a fixed
  reason per case type
- (b) second pass, only when a check is needed: the same prompt with the gateway's results for the gold checks,
  no more checks allowed -> DECISION. Same prompts as src/monitor/loop.py's selective setting
- policies (PLAN 16.4): the gold policies plus the best retrieved other policies, 3 in all, under local numbers
  in a fixed random order per record (prompt_builder.number_policies); targets cite numbers, never policy ids
- (a) and (b) repeated 2x on train (PLAN 16.5), once on val
Phase B stops before writing anything until every check-needed record has gold.required_checks (seed_to_record.md
D4) and the check gateway exists (src/gateway, Step 4): check examples without them would teach wrong checks.
The SFT files hold record text, so they are git-ignored (AgentRisk has no licence). Length filtering happens in
train_lora.py, with the real tokenizer.
"""
import argparse
import importlib.util
import json
import re
import sys
from collections import Counter

from src.common.io import REPO_ROOT, read_jsonl, write_json, write_jsonl
from src.monitor.check_tools import load_check_tools
from src.monitor.parser import parse_output
from src.monitor.prompt_builder import (DECIDE_TEMPLATE, RISK_TEMPLATE, as_messages, build_decide_prompt,
                                        build_risk_prompt, ids_to_refs, number_policies)

EXT = REPO_ROOT / "data" / "external"
RECORDS = REPO_ROOT / "data" / "records"
OUT = REPO_ROOT / "data" / "training"
SOURCES = ("r_judge", "atbench", "agentrisk")
REPEAT_OURS = 2             # PLAN 16.5: so the external examples do not drown ours
N_POLICIES = 3              # gold + look-alikes shown per example (PLAN 16.4)
POLICY_ID = re.compile(r"\bP_[A-Z]+_\d+\b")
# NEED_INFORMATION reason per case (at most 30 words, R9.1); {fact} is the gold missing_fact
REASONS = {
    ("T1", None): "No tool result in the conversation shows the {fact}, and the decision depends on it.",
    ("T2", "b"): "The only tool result is about a different resource, so the {fact} is not known.",
    ("T2", "c"): "The resource changed after the last tool result about it, so the {fact} is no longer known.",
    ("T2", "d"): "Only the agent states the {fact}, and what the agent says is not proof.",
    ("T5", None): "No tool result in the conversation shows the {fact}, and the decision depends on it.",
}


# ---------------------------------------------------------------- (c) risk examples (Phase A and B)

def risk_target(gold: dict) -> str:
    """The answer the model must give, in the RISK format of prompts/monitor_risk_v1.txt."""
    if gold["risk_label"] not in ("SAFE", "UNSAFE") or not gold["risk_type"]:
        raise ValueError(f"no final label: {gold['risk_label']!r} / {gold['risk_type']!r}")
    return json.dumps({"type": "RISK", "risk_label": gold["risk_label"], "risk_type": gold["risk_type"]})


def example(rec: dict) -> dict:
    return {"record_id": rec["record_id"], "source": rec["source"], "kind": "risk",
            "messages": as_messages(build_risk_prompt(rec["visible"])), "target": risk_target(rec["gold"])}


def counts(rows: list[dict]) -> dict:
    return {"examples": len(rows), "by_source": dict(Counter(r["source"] for r in rows)),
            "by_target": dict(Counter(r["target"] for r in rows).most_common())}


def build(train_ids: set[str]) -> tuple[list[dict], list[dict], dict]:
    train, val = [], []
    for name in SOURCES:
        for rec in read_jsonl(EXT / f"{name}.jsonl"):
            if rec["record_id"] in train_ids:
                train.append(example(rec))
            elif rec["split"] == "val":
                val.append(example(rec))
    missing = train_ids - {e["record_id"] for e in train}
    if missing:
        raise ValueError(f"{len(missing)} Phase A ids not found, e.g. {sorted(missing)[:3]}")
    stats = {"kind": "risk (c) only, Phase A", "prompt": RISK_TEMPLATE, "train": counts(train), "val": counts(val)}
    return train, val, stats


# ---------------------------------------------------------------- (a) and (b) from our records (Phase B)

class NotReady(Exception):
    """Phase B inputs that other steps still have to provide."""


def decision_target(gold: dict, numbered: list[dict]) -> str:
    return json.dumps({"type": "DECISION", "decision": gold["decision"], "risk_label": gold["risk_label"],
                       "risk_type": gold["risk_type"],
                       "evidence": {"facts": list(gold["evidence"]["facts"]),
                                    "policy_ids": ids_to_refs(gold["evidence"]["policy_ids"], numbered)}})


def need_information_target(rec: dict) -> str:
    gold = rec["gold"]
    reason = REASONS[(rec["case_type"], rec["subtype"])].format(fact=gold["missing_fact"])
    return json.dumps({"type": "NEED_INFORMATION", "reason": reason, "missing_fact": gold["missing_fact"],
                       "checks": [{"tool": c["tool"], "args": dict(c["args"])} for c in gold["required_checks"]]})


def shown_policies(rec: dict, by_id: dict[str, dict], retriever) -> list[dict]:
    """The gold policies plus the best-ranked other policies, N_POLICIES in all (PLAN 16.4)."""
    from src.policies.retriever import query_for
    gold = [by_id[p] for p in rec["gold"]["policy_ids"]]
    need = max(0, N_POLICIES - len(gold))
    ranked = retriever.search(query_for(rec["visible"]), k=need + len(gold)) if need else []
    others = [p for p in ranked if p["policy_id"] not in rec["gold"]["policy_ids"]][:need]
    return [{"policy_id": p["policy_id"], "text": p["text"]} for p in gold + others]


def our_examples(rec: dict, by_id: dict[str, dict], retriever, check_tools: list[dict], gateway_for) -> list[dict]:
    """(a), plus (b) when a check is needed, for one record."""
    numbered = number_policies(shown_policies(rec, by_id, retriever), rec["record_id"])
    gold, visible = rec["gold"], rec["visible"]
    base = {"record_id": rec["record_id"], "source": rec["source"], "case_type": rec["case_type"]}
    first = build_decide_prompt(visible, numbered, check_tools, may_check=True)
    if not gold["check_needed"]:
        return [dict(base, kind="first_pass", messages=as_messages(first), target=decision_target(gold, numbered))]
    gateway = gateway_for(rec)
    results = []
    for c in gold["required_checks"]:
        result = gateway.call(c["tool"], c["args"])
        if isinstance(result, dict) and "error" in result:
            raise ValueError(f"{rec['record_id']}: gold check {c} fails: {result}")
        results.append({"tool": c["tool"], "args": c["args"], "result": result})
    second = build_decide_prompt(visible, numbered, check_tools, may_check=False, results=results)
    return [dict(base, kind="first_pass", messages=as_messages(first), target=need_information_target(rec)),
            dict(base, kind="second_pass", messages=as_messages(second), target=decision_target(gold, numbered))]


def check_example(ex: dict) -> None:
    """The target parses as the loop would parse it, and no policy id is in the prompt or the target."""
    allowed = ("DECISION", "NEED_INFORMATION") if ex["kind"] == "first_pass" else ("DECISION",)
    if parse_output(ex["target"], allowed) is None:
        raise ValueError(f"{ex['record_id']}: target is not a valid {allowed} answer: {ex['target']}")
    if POLICY_ID.search(ex["messages"][0]["content"] + ex["target"]):
        raise ValueError(f"{ex['record_id']}: a policy id reaches the prompt or the target")


def phase1(records: list[dict], split: str) -> list[dict]:
    """The records of one split whose tools are all phase 1 (scripts/split_by_phase.py buckets)."""
    spec = importlib.util.spec_from_file_location("split_by_phase", REPO_ROOT / "scripts" / "split_by_phase.py")
    sbp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sbp)
    keep = sbp.split_records(records, sbp.load_phases(REPO_ROOT / "configs" / "tool_phases.yaml"))["phase1"]
    bad = [r["record_id"] for r in keep if r["set"] != "in_domain" or r["split"] != split]
    if bad:
        raise ValueError(f"not in_domain {split} records: {bad[:5]}")
    return keep


def readiness(records: list[dict], check_names: set[str], gateway_for) -> list[str]:
    """What is still missing before Phase B can be built; empty when ready."""
    todo = []
    no_checks = [r["record_id"] for r in records if r["gold"]["check_needed"] and not r["gold"]["required_checks"]]
    if no_checks:
        todo.append(f"{len(no_checks)} check-needed records have no gold.required_checks (seed_to_record.md D4), "
                    f"e.g. {no_checks[:3]}")
    unknown = sorted({c["tool"] for r in records for c in r["gold"]["required_checks"] or []} - check_names)
    if unknown:
        todo.append(f"required checks name tools that configs/check_tools.yaml does not have: {unknown}")
    if gateway_for is None:
        todo.append("no check gateway: src/gateway/gateway.py needs for_record(record) -> object with "
                    "call(tool, args) -> dict, the same gateway the monitor loop uses (Step 4)")
    return todo


def default_gateway_factory():
    try:
        from src.gateway.gateway import for_record
    except ImportError:
        return None
    return for_record


def build_phase_b(train_records: list[dict], val_records: list[dict], external: tuple[list, list], policies: list[dict],
                  retriever, check_tools: list[dict], gateway_for) -> tuple[list[dict], list[dict], dict]:
    todo = readiness(train_records + val_records, {t["name"] for t in check_tools}, gateway_for)
    if todo:
        raise NotReady("; ".join(todo))
    by_id = {p["policy_id"]: p for p in policies}
    ours = {}
    for name, rows in (("train", train_records), ("val", val_records)):
        ours[name] = [ex for r in rows for ex in our_examples(r, by_id, retriever, check_tools, gateway_for)]
        for ex in ours[name]:
            check_example(ex)
    ext_train, ext_val = external
    train = ours["train"] * REPEAT_OURS + ext_train
    val = ours["val"] + ext_val

    def mix(rows):
        return dict(counts(rows), by_kind=dict(Counter(r["kind"] for r in rows)),
                    ours_by_case_type=dict(sorted(Counter(r["case_type"] for r in rows if "case_type" in r).items())))
    stats = {"kind": "Phase B: (a) first pass + (b) second pass from our phase 1 records (x2 on train) + (c) risk",
             "prompts": {"ours": DECIDE_TEMPLATE, "risk": RISK_TEMPLATE}, "repeat_ours": REPEAT_OURS,
             "records": {"train": len(train_records), "val": len(val_records)}, "train": mix(train), "val": mix(val)}
    return train, val, stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["a", "b"], default="a")
    args = ap.parse_args(argv)
    ids = set((EXT / "splits" / "phase_a_train.txt").read_text(encoding="utf-8").split())
    ext_train, ext_val, stats = build(ids)
    stats_name = "stats.json"
    if args.phase == "a":
        train, val = ext_train, ext_val
    else:
        from src.policies.retriever import Retriever
        from src.policies.store import IN_DOMAIN, load_policies
        train_records = phase1(list(read_jsonl(RECORDS / "train.jsonl")), "train")
        val_records = phase1(list(read_jsonl(RECORDS / "val.jsonl")), "val")
        check_tools = load_check_tools()
        gateway_for = default_gateway_factory()
        todo = readiness(train_records + val_records, {t["name"] for t in check_tools}, gateway_for)
        if todo:            # before loading the embedding model
            print("Phase B is not ready, nothing written:\n- " + "\n- ".join(todo), file=sys.stderr)
            return 1
        policies = load_policies(IN_DOMAIN)
        train, val, stats = build_phase_b(train_records, val_records, (ext_train, ext_val), policies,
                                          Retriever(policies), check_tools, gateway_for)
        stats_name = "stats_phase_b.json"
    write_jsonl(OUT / "sft_train.jsonl", train)
    write_jsonl(OUT / "sft_val.jsonl", val)
    write_json(OUT / stats_name, stats)
    print(f"sft_train {len(train)}, sft_val {len(val)} -> {OUT.relative_to(REPO_ROOT)} ({stats_name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
