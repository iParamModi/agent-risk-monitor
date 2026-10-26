"""Builds data/external/agentrisk_recheck.csv: the AgentRisk items that need a person, split over 4 labellers.

  python scripts/make_agentrisk_recheck.py            (risk type sheet; needs `python -m src.external.agentrisk` first)
  python scripts/make_agentrisk_recheck.py --cause    (risk cause sheet: data/external/agentrisk_cause_recheck.csv)

Risk cause (review sheet Q4): each risk driver points to one or two of our causes (DRIVER_CAUSES); an
item's options are the causes of all its drivers. One option: decided by the map. More: a person picks.

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
from src.external.agentrisk import DRIVER_CAUSES, cause_options, needs_person  # noqa: E402,F401  (map lives there)

RECORDS = REPO_ROOT / "data" / "external" / "agentrisk.jsonl"
SHEET = REPO_ROOT / "data" / "external" / "agentrisk_recheck.csv"
LABELLERS = ("Meet", "Param", "Prateek", "Moiesha")
SEED = 20261026
COLUMNS = ["record_id", "assigned_to", "split", "reason", "options", "recheck_type", "recheck_note"]

CAUSE_SHEET = REPO_ROOT / "data" / "external" / "agentrisk_cause_recheck.csv"
CAUSE_COLUMNS = ["record_id", "assigned_to", "split", "reason", "options", "recheck_cause", "recheck_note"]
CAUSE_LABELLERS = ("Meet",)    # all 281, by hand (Meet took it back from Prateek, 2026-10-26)


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


def select_cause(records: list[dict]) -> list[dict]:
    """UNSAFE items whose drivers give more than one candidate cause."""
    out = []
    for r in records:
        if r["gold"]["risk_label"] != "UNSAFE":
            continue
        drivers = r["gold"]["native_labels"]["risk_drivers"]
        options = cause_options(drivers)
        if len(options) > 1:
            reason = "two drivers" if len(drivers) == 2 else "one driver"
            out.append({"record_id": r["record_id"], "split": r["split"], "reason": reason, "options": options,
                        "group": (r["split"], reason, " + ".join(sorted(drivers)))})
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
    cause = "--cause" in sys.argv
    sheet, columns, labellers = (CAUSE_SHEET, CAUSE_COLUMNS, CAUSE_LABELLERS) if cause else (SHEET, COLUMNS, LABELLERS)
    if sheet.exists():
        with open(sheet, encoding="utf-8", newline="") as f:
            if any((r.get(columns[5]) or "").strip() or (r.get("recheck_note") or "").strip() for r in csv.DictReader(f)):
                print(f"{sheet.name} already has labels; not overwriting")
                return 1
    records = list(read_jsonl(RECORDS))
    items = select_cause(records) if cause else select(records)
    assign(items, labellers)
    items.sort(key=lambda it: int(it["record_id"][3:]))
    with open(sheet, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(columns)
        for it in items:
            w.writerow([it["record_id"], it["assigned_to"], it["split"], it["reason"], " | ".join(it["options"]), "", ""])
    print(f"{sheet.name}: {len(items)} items: " + ", ".join(f"{k} {v}" for k, v in Counter(it["reason"] for it in items).items()))
    if cause:
        unsafe = sum(r["gold"]["risk_label"] == "UNSAFE" for r in records)
        print(f"  decided by the driver map alone: {unsafe - len(items)}")
    for name in labellers:
        mine = [it for it in items if it["assigned_to"] == name]
        print(f"  {name}: {len(mine)} ({', '.join(f'{k} {v}' for k, v in sorted(Counter(it['reason'] for it in mine).items()))}; "
              f"{', '.join(f'{k} {v}' for k, v in sorted(Counter(it['split'] for it in mine).items()))})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
