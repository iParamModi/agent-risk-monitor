"""Shows your AgentRisk per-record rows with AgentRisk's own released labels (no label made by us or an LLM).

Run: python scripts/show_agentrisk_recheck.py <YourName>             (all your rows)
     python scripts/show_agentrisk_recheck.py Param,Prateek,Moiesha  (several people in one file)
     python scripts/show_agentrisk_recheck.py <YourName> AR-123      (one record)
     python scripts/show_agentrisk_recheck.py --check                (spelling / options check, all rows)
How-to: data/external/agentrisk_recheck_HOWTO.md. Sheet made by scripts/make_agentrisk_recheck.py.
Covers the UNSAFE AgentRisk items that need a person (review sheet Q2 + Q3):
  reason "mixed domain": harm domain Operational / Service or Information Quality (situation rule below)
  reason "two domains":  two harm domains that Meet's Q2 map turns into two different types
Prints the trajectory, the proposed action, and AgentRisk's released labels (severity, harm domains with
Meet's Q2 map, risk drivers). The items are not in git: run `python -m src.external.agentrisk` first.
Labels are typed by hand into data/external/agentrisk_recheck.csv with
data/external/risk_type_categories.txt and the rules below; no LLM may suggest or fill them (CLAUDE.md section 6).

Situation rule (Meet, 2026-10-26):
  system made unstable, forced shutdown, processes killed   -> SECURITY
  files moved or hidden without consent                     -> SECURITY
  deleting apps or files, clearing data, overwriting records -> DATA_LOSS
  physical or emergency harm (dispatch, health)             -> OTHER
  none of these: use the guide's decision order (any of the 6 types), or CONFUSED
Two domains (Meet, 2026-10-26): read the conversation and pick the type of the harm the proposed action
itself causes (guide Rule 2). Pick ONLY from the row's options (or CONFUSED).
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHEET = ROOT / "data" / "external" / "agentrisk_recheck.csv"
RECORDS = ROOT / "data" / "external" / "agentrisk"
MAX_TOOL_CHARS = 2000
Q2_MAP = {     # Meet's review-sheet Q2 answers (data/external/agentrisk_map_review.md)
    "Privacy / Confidentiality": "PRIVACY_LEAKAGE", "Security / System Integrity": "SECURITY",
    "Financial / Assets": "FINANCIAL_LOSS", "Physical / Health": "OTHER", "Legal / Compliance": "OTHER",
    "Reputational / Social / Psychological": "OTHER", "Environmental": "OTHER", "Discrimination / Fairness": "OTHER",
    "Operational / Service": "by situation", "Information Quality": "by situation",
}


def show(row: dict, n: int, total: int) -> None:
    path = RECORDS / f"{row['record_id']}.json"
    if not path.exists():
        raise SystemExit(f"{path} missing: run `python -m src.external.agentrisk` first")
    rec = json.loads(path.read_text(encoding="utf-8"))
    print("=" * 80)
    print(f"[{n}/{total}] {row['record_id']}   (split: {row['split']}, {row['reason']})   for: {row['assigned_to']}   "
          f"done: {row['recheck_type'] or '-'}")
    print("=" * 80)
    for step in rec["visible"]["trajectory"]:
        print(f"\n--- {step['role']} ---")
        text = step.get("text") or ""
        if step["role"] == "tool" and len(text) > MAX_TOOL_CHARS:
            text = text[:MAX_TOOL_CHARS] + f"\n... [{len(text) - MAX_TOOL_CHARS} more characters cut]"
        if text:
            print(text)
        if step.get("action_text"):
            print(f"ACTION: {step['action_text']}")
    print(f"\n>>> PROPOSED ACTION (not yet run): {rec['visible']['proposed_action_text']}")
    print(f">>> CHOOSE ONE OF: {row['options']}   (or CONFUSED)")
    labels = rec["gold"]["native_labels"]
    domains = ", ".join(f"{d} (your map: {Q2_MAP.get(d, '?')})" for d in labels["risk_domains"])
    print(f"\nAgentRisk labels: severity {labels['risk_severity']} | harm domains: {domains} | "
          f"risk drivers: {', '.join(labels['risk_drivers'])}\n")


def check() -> int:
    """Every filled recheck_type must be one of the row's options or CONFUSED."""
    with open(SHEET, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    bad = [(r["record_id"], r["assigned_to"], r["recheck_type"]) for r in rows
           if r["recheck_type"].strip() and r["recheck_type"].strip() not in r["options"].split(" | ") + ["CONFUSED"]]
    spaces = [r["record_id"] for r in rows if r["recheck_type"] != r["recheck_type"].strip()]
    for name in sorted({r["assigned_to"] for r in rows}):
        mine = [r for r in rows if r["assigned_to"] == name]
        print(f"{name}: {sum(bool(r['recheck_type'].strip()) for r in mine)}/{len(mine)} filled")
    for rid, who, value in bad:
        print(f"  NOT AN OPTION: {rid} ({who}): {value!r}")
    if spaces:
        print(f"  extra spaces (harmless, will be stripped): {', '.join(spaces)}")
    return 1 if bad else 0


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    if sys.argv[1] == "--check":
        return check()
    names, only = [n.strip().lower() for n in sys.argv[1].split(",")], set(sys.argv[2:])
    with open(SHEET, encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["assigned_to"].lower() in names]
    rows.sort(key=lambda r: names.index(r["assigned_to"].lower()))      # grouped by person, in the order given
    name = sys.argv[1]
    if only:
        rows = [r for r in rows if r["record_id"] in only]
    if not rows:
        print(f"no rows for {name!r} in {SHEET.name}")
        return 1
    for n, row in enumerate(rows, 1):
        show(row, n, len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
