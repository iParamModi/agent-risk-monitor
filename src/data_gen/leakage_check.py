"""A/B identity script (DATASET.md section 3.6): the two records of a T1 pair must look the same to the model.

For every T1 seed: the visible part (trajectory and proposed action) plus the gold policy ids, as canonical JSON
(sorted keys, no extra spaces), must be identical for A and B, while the hidden key fact and the gold decision
differ. No tool result may show either side's hidden value. A pair that fails would let a monitor that never
checks tell A from B, so the pair would no longer measure checking. Every failed pair stops the merge (we do not
drop records); the list goes to data/generated/reports/leakage.json.
"""
import json
from collections import defaultdict

from src.data_gen.auto_checks import spellings


def canonical_visible(rec: dict) -> str:
    part = {"trajectory": rec["visible"]["trajectory"], "proposed_action": rec["visible"]["proposed_action"],
            "policy_ids": rec["gold"]["policy_ids"]}
    return json.dumps(part, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def check_pair(a: dict | None, b: dict | None) -> list[str]:
    """Reasons the pair fails; empty if it passes."""
    if a is None or b is None:
        return ["A or B is missing"]
    reasons = []
    if canonical_visible(a) != canonical_visible(b):
        reasons.append("visible part differs between A and B")
    if a["hidden"]["key_facts"] == b["hidden"]["key_facts"]:
        reasons.append("hidden key fact is the same on both sides")
    if a["gold"]["decision"] == b["gold"]["decision"]:
        reasons.append(f"same gold decision {a['gold']['decision']} on both sides")
    tool_text = "\n".join(m["text"] or "" for m in a["visible"]["trajectory"] if m["role"] == "tool")
    for side in (a, b):
        for key, value in side["hidden"]["key_facts"].items():
            reasons += [f"a tool result shows {side['pair_side']}'s hidden value {s!r} ({key})"
                        for s in spellings(value) if s in tool_text]
    return reasons


def check_pairs(records: list[dict]) -> dict:
    """{"pairs": n, "failed": [{"seed_id", "reasons"}]} over all T1 records."""
    sides = defaultdict(dict)
    for r in records:
        if r["case_type"] == "T1":
            sides[r["seed_id"]][r["pair_side"]] = r
    failed = []
    for sid in sorted(sides):
        reasons = check_pair(sides[sid].get("A"), sides[sid].get("B"))
        if reasons:
            failed.append({"seed_id": sid, "reasons": reasons})
    return {"pairs": len(sides), "failed": failed}
