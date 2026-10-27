"""Step 9 merge (docs/seed_to_record.md section 8): data/generated/<T1..T5>/*.json -> data/records/.

    python -m src.data_gen.merge        (make records runs this, then python -m src.data_gen.split)

1. Loads the three people's record files (data/generated/T1..T5) and all seeds.
2. Puts every record in one shape. The chunks differ in two places:
   - hidden.state: Meet's chunk has {"start_state", "resolved_facts"}; Param's and Prateek's have the flat true
     state with the variant's hidden values on the entities (section 4, hidden.state). Meet's start_state is
     already the state at the proposed action (writes applied), so each resolved fact is set on its entity; a
     fact that no single entity holds (a count of admins) stays in key_facts only, as in Param's chunk.
     resolved_facts must equal key_facts.
   - gold.native_labels: missing in Param's chunk, set to null as in the other two.
   Fields keep the order of section 10.1. Nothing else changes.
3. meta.n_tokens = Qwen3 token count of the visible part (src/common/tokens.py).
4. Runs every check in auto_checks.py and leakage_check.py. One problem stops the merge: nothing is written.
5. Writes data/records/all_in_domain.jsonl and all_ood.jsonl, sorted by record_id (split still null), plus
   data/generated/reports/merge_report.json (counts, what was normalised, flags for a human) and leakage.json.
"""
import copy
import json
import sys
from collections import Counter
from pathlib import Path

import yaml

from src.common.io import REPO_ROOT, write_json, write_jsonl
from src.common.seed import set_seed
from src.data_gen.auto_checks import check_dataset, check_record, find_entities, split_fact_key
from src.data_gen.leakage_check import check_pairs
from src.policies.store import IN_DOMAIN, OOD, load_policies

GENERATED = REPO_ROOT / "data" / "generated"
RECORDS = REPO_ROOT / "data" / "records"
REPORTS = GENERATED / "reports"
SEEDS = REPO_ROOT / "data" / "seeds"
TOOL_PHASES = REPO_ROOT / "configs" / "tool_phases.yaml"
CHECK_TOOLS = REPO_ROOT / "configs" / "check_tools.yaml"
CASE_DIRS = ("T1", "T2", "T3", "T4", "T5")
RECORD_KEYS = ("record_id", "seed_id", "source", "set", "split", "domain", "case_type", "subtype", "pair_side",
               "version", "task", "visible", "hidden", "gold", "meta")
VISIBLE_KEYS = ("trajectory", "proposed_action", "proposed_action_text")
HIDDEN_KEYS = ("state", "key_facts")
GOLD_KEYS = ("decision", "risk_label", "risk_type", "risk_cause", "check_needed", "required_checks",
             "missing_fact", "policy_ids", "evidence", "native_labels", "source_note", "source_taxonomy")
META_KEYS = ("writer_llm", "generator_version", "n_tokens", "ood_shift")
OUT_FILES = {"in_domain": "all_in_domain.jsonl", "ood": "all_ood.jsonl"}


def load_generated(folder: Path = GENERATED) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for d in CASE_DIRS for p in sorted((folder / d).glob("*.json"))]


def load_seeds(folder: Path = SEEDS) -> dict[str, dict]:
    seeds = {}
    for p in sorted(folder.glob("*/*.yaml")):
        seed = yaml.safe_load(p.read_text(encoding="utf-8"))
        seeds[seed["seed_id"]] = seed
    return seeds


def read_tool_names(path: Path = TOOL_PHASES) -> set[str]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {t for part in raw.values() if isinstance(part, dict) for t in part.get("read", [])}


def chunk_owner(seeds: dict[str, dict]) -> dict[str, str]:
    """seed_id -> who generated it (section 8: sorted seed ids, index % 3)."""
    return {sid: ("Param", "Prateek", "Meet")[i % 3] for i, sid in enumerate(sorted(seeds))}


def ordered(d: dict, keys: tuple[str, ...]) -> dict:
    extra = [k for k in d if k not in keys]
    if extra:
        raise ValueError(f"unexpected fields {extra}")
    return {k: d[k] for k in keys if k in d}


def flatten_state(hidden: dict) -> tuple[dict, list[str]]:
    """Meet's {"start_state", "resolved_facts"} -> {"state": flat true state, "key_facts"}; other shapes unchanged.
    Returns (hidden, notes)."""
    state = hidden["state"]
    if set(state) != {"start_state", "resolved_facts"}:
        return hidden, []
    if state["resolved_facts"] != hidden["key_facts"]:
        raise ValueError(f"resolved_facts {state['resolved_facts']} != key_facts {hidden['key_facts']}")
    flat = copy.deepcopy(state["start_state"])
    notes = ["flattened hidden.state"]
    for key, value in state["resolved_facts"].items():
        resource, attribute = split_fact_key(key)
        hits = find_entities(flat, resource)
        if len(hits) == 1:
            hits[0][1][attribute] = value        # the entity dict inside `flat`
        else:
            notes.append(f"kept {key} in key_facts only ({len(hits)} entities named {resource!r})")
    return {"state": flat, "key_facts": hidden["key_facts"]}, notes


def normalize(rec: dict) -> tuple[dict, list[str]]:
    """One record in the common shape; returns (record, notes on what changed)."""
    hidden, notes = flatten_state(rec["hidden"])
    gold = dict(rec["gold"])
    if "native_labels" not in gold:
        gold["native_labels"] = None
        notes.append("added gold.native_labels = null")
    out = dict(rec, visible=ordered(rec["visible"], VISIBLE_KEYS), hidden=ordered(hidden, HIDDEN_KEYS),
               gold=ordered(gold, GOLD_KEYS), meta=ordered(rec["meta"], META_KEYS))
    return ordered(out, RECORD_KEYS), notes


def load_check_specs(path: Path = CHECK_TOOLS) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def merge(raw: list[dict], seeds: dict[str, dict], tokenizer, stores: dict[str, set[str]],
          read_tools: set[str], check_specs: dict | None = None) -> tuple[list[dict], dict, dict]:
    """(records, report, leakage). The report lists problems (any problem = do not write) and flags.
    tokenizer None leaves meta.n_tokens null (tests)."""
    from src.common.tokens import count_tokens
    records, notes = [], {}
    for r in raw:
        rec, n = normalize(r)
        rec["meta"]["n_tokens"] = None if tokenizer is None else count_tokens(rec, tokenizer)
        records.append(rec)
        if n:
            notes[rec["record_id"]] = n
    problems, flags = [], []
    for rec in records:
        if rec.get("seed_id") in seeds:
            p, f = check_record(rec, seeds[rec["seed_id"]], stores[rec["set"]], read_tools, check_specs)
            problems += p
            flags += f
    problems += check_dataset(records, seeds)
    leakage = check_pairs(records)
    problems += [f"{x['seed_id']}: T1 pair: {reason}" for x in leakage["failed"] for reason in x["reasons"]]
    owner = chunk_owner(seeds)
    tokens = sorted(r["meta"]["n_tokens"] for r in records if r["meta"]["n_tokens"] is not None)
    report = {
        "records": len(records), "seeds": len({r["seed_id"] for r in records}),
        "by_set": dict(Counter(r["set"] for r in records)),
        "by_case_type": dict(sorted(Counter(r["case_type"] for r in records).items())),
        "by_decision": dict(sorted(Counter(r["gold"]["decision"] for r in records).items())),
        "by_risk_type": dict(sorted(Counter(r["gold"]["risk_type"] for r in records).items())),
        "by_chunk": dict(sorted(Counter(owner.get(r["seed_id"], "?") for r in records).items())),
        "writer_llm": dict(Counter(r["meta"]["writer_llm"] for r in records)),
        "n_tokens": {"max": tokens[-1], "median": tokens[len(tokens) // 2]} if tokens else None,
        "normalised": {"records": len(notes),
                       "what": dict(Counter(n.split(" (")[0] if n.startswith("kept") else n
                                            for ns in notes.values() for n in ns)),
                       "kept_in_key_facts_only": {rid: [n for n in ns if n.startswith("kept")]
                                                  for rid, ns in notes.items() if any(n.startswith("kept") for n in ns)}},
        "t1_pairs": leakage["pairs"], "t1_pairs_failed": len(leakage["failed"]),
        # D4: check-needed records whose gold checks are not filled yet (Phase B and the oracle need 0)
        "required_checks_missing": sum(r["gold"]["check_needed"] and not r["gold"]["required_checks"] for r in records),
        "problems": problems, "flags": flags,
    }
    return records, report, leakage


def main() -> int:
    set_seed(42)
    from src.common.tokens import load_tokenizer
    seeds = load_seeds()
    stores = {"in_domain": {p["policy_id"] for p in load_policies(IN_DOMAIN)},
              "ood": {p["policy_id"] for p in load_policies(OOD)}}
    records, report, leakage = merge(load_generated(), seeds, load_tokenizer(), stores, read_tool_names(),
                                     load_check_specs())
    write_json(REPORTS / "merge_report.json", report)
    write_json(REPORTS / "leakage.json", leakage)
    print(json.dumps({k: report[k] for k in ("records", "seeds", "by_set", "by_chunk", "n_tokens", "t1_pairs",
                                             "t1_pairs_failed", "required_checks_missing")}))
    print(f"normalised {report['normalised']['records']} records: {report['normalised']['what']}")
    print(f"{len(report['flags'])} flags for a human (merge_report.json)")
    if report["problems"]:
        for p in report["problems"]:
            print("PROBLEM", p)
        print(f"{len(report['problems'])} problems: nothing written", file=sys.stderr)
        return 1
    for name, file in OUT_FILES.items():
        rows = sorted((r for r in records if r["set"] == name), key=lambda r: r["record_id"])
        print(f"wrote {write_jsonl(RECORDS / file, rows)} records to {RECORDS / file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
