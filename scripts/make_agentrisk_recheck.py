"""Builds data/external/agentrisk_recheck.csv: the AgentRisk items that need a person, split over 4 labellers.

  python scripts/make_agentrisk_recheck.py            (needs `python -m src.external.agentrisk` first)

Which items (UNSAFE only; review sheet Q2 + Q3, Meet 2026-10-26):
  "two domains"  : two harm domains that Meet's Q2 map turns into two different types
                   -> options = those 2 types
  "mixed domain" : a domain with no single type (Operational / Service, Information Quality)
                   -> options = the situation-rule types SECURITY, DATA_LOSS, OTHER
                      + the mapped type of the other domain, if any
Single-domain items and pairs that map to the same type need no person (the map decides).
Labellers only pick from `options` (or CONFUSED), so the label stays one of the item's own harms.
Split: within each (data split, reason, domain pair) group the items are shuffled (seed 20261026) and dealt in
turn to the 4 labellers, so everyone gets a similar mix. The file is never overwritten once a label
is filled. No LLM may suggest or fill labels (CLAUDE.md section 6).
"""
import csv
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.common.io import REPO_ROOT, read_jsonl  # noqa: E402

RECORDS = REPO_ROOT / "data" / "external" / "agentrisk.jsonl"
SHEET = REPO_ROOT / "data" / "external" / "agentrisk_recheck.csv"
LABELLERS = ("Meet", "Param", "Prateek", "Moiesha")
SEED = 20261026
TYPE_ORDER = ("FINANCIAL_LOSS", "DATA_LOSS", "ACCESS_CONTROL", "SECURITY", "PRIVACY_LEAKAGE", "OTHER")   # guide order
Q2_MAP = {     # Meet's review-sheet Q2 answers (data/external/agentrisk_map_review.md)
    "Privacy / Confidentiality": "PRIVACY_LEAKAGE", "Security / System Integrity": "SECURITY",
    "Financial / Assets": "FINANCIAL_LOSS", "Physical / Health": "OTHER", "Legal / Compliance": "OTHER",
    "Reputational / Social / Psychological": "OTHER", "Environmental": "OTHER", "Discrimination / Fairness": "OTHER",
}
MIXED = {"Operational / Service", "Information Quality"}
SITUATION_TYPES = {"SECURITY", "DATA_LOSS", "OTHER"}
COLUMNS = ["record_id", "assigned_to", "split", "reason", "options", "recheck_type", "recheck_note"]


def ordered(types: set[str]) -> list[str]:
    return [t for t in TYPE_ORDER if t in types]


def needs_person(domains: list[str]) -> tuple[str, list[str]] | None:
    """(reason, options) for an UNSAFE item, or None when the map alone decides."""
    if MIXED & set(domains):
        return "mixed domain", ordered(SITUATION_TYPES | {Q2_MAP[d] for d in domains if d not in MIXED})
    mapped = {Q2_MAP[d] for d in domains}
    if len(mapped) == 2:
        return "two domains", ordered(mapped)
    return None


def select(records: list[dict]) -> list[dict]:
    out = []
    for r in records:
        if r["gold"]["risk_label"] != "UNSAFE":
            continue
        domains = r["gold"]["native_labels"]["risk_domains"]
        need = needs_person(domains)
        if need:
            out.append({"record_id": r["record_id"], "split": r["split"], "reason": need[0], "options": need[1],
                        "group": (r["split"], need[0], " + ".join(sorted(domains)))})
    return out


def assign(items: list[dict], labellers=LABELLERS, seed: int = SEED) -> None:
    """Deal each group's shuffled items in turn; the next group starts with whoever has the fewest so far."""
    rng = random.Random(seed)
    groups = defaultdict(list)
    for it in sorted(items, key=lambda it: int(it["record_id"][3:])):
        groups[it["group"]].append(it)
    load = Counter({name: 0 for name in labellers})
    for key in sorted(groups):
        members = groups[key]
        rng.shuffle(members)
        order = sorted(labellers, key=lambda n: (load[n], labellers.index(n)))
        for i, it in enumerate(members):
            it["assigned_to"] = order[i % len(order)]
            load[it["assigned_to"]] += 1


def main() -> int:
    if SHEET.exists():
        with open(SHEET, encoding="utf-8", newline="") as f:
            if any((r.get("recheck_type") or "").strip() or (r.get("recheck_note") or "").strip() for r in csv.DictReader(f)):
                print(f"{SHEET.name} already has labels; not overwriting")
                return 1
    items = select(list(read_jsonl(RECORDS)))
    assign(items)
    items.sort(key=lambda it: int(it["record_id"][3:]))
    with open(SHEET, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for it in items:
            w.writerow([it["record_id"], it["assigned_to"], it["split"], it["reason"], " | ".join(it["options"]), "", ""])
    print(f"{len(items)} items: " + ", ".join(f"{k} {v}" for k, v in Counter(it["reason"] for it in items).items()))
    for name in LABELLERS:
        mine = [it for it in items if it["assigned_to"] == name]
        print(f"  {name}: {len(mine)} ({', '.join(f'{k} {v}' for k, v in sorted(Counter(it['reason'] for it in mine).items()))}; "
              f"{', '.join(f'{k} {v}' for k, v in sorted(Counter(it['split'] for it in mine).items()))})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
