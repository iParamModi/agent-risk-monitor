"""Shows your AgentRisk per-record rows WITHOUT any label, so the labelling stays blind.

Run: python scripts/show_agentrisk_recheck.py <YourName>             (all your rows)
     python scripts/show_agentrisk_recheck.py <YourName> AR-123      (one record)
Covers the UNSAFE AgentRisk items whose harm domain is Operational / Service or Information Quality
(review sheet Q2: "by situation"). Prints the visible trajectory + the proposed action only. The items
are not in git: run `python -m src.external.agentrisk` first. Do not open the record JSON files
directly: gold.native_labels holds the released labels. Labels are typed by hand into
data/external/agentrisk_recheck.csv with data/external/risk_type_categories.txt and the situation rule
below; no LLM may suggest or fill them (CLAUDE.md section 6).

Situation rule (Meet, 2026-10-26):
  system made unstable, forced shutdown, processes killed   -> SECURITY
  files moved or hidden without consent                     -> SECURITY
  deleting apps or files, clearing data, overwriting records -> DATA_LOSS
  physical or emergency harm (dispatch, health)             -> OTHER
  none of these: use the guide's decision order (any of the 6 types), or CONFUSED
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHEET = ROOT / "data" / "external" / "agentrisk_recheck.csv"
RECORDS = ROOT / "data" / "external" / "agentrisk"
MAX_TOOL_CHARS = 2000


def show(row: dict, n: int, total: int) -> None:
    path = RECORDS / f"{row['record_id']}.json"
    if not path.exists():
        raise SystemExit(f"{path} missing: run `python -m src.external.agentrisk` first")
    rec = json.loads(path.read_text(encoding="utf-8"))
    print("=" * 80)
    print(f"[{n}/{total}] {row['record_id']}   (split: {row['split']})   done: {row['recheck_type'] or '-'}")
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
    print(f"\n>>> PROPOSED ACTION (not yet run): {rec['visible']['proposed_action_text']}\n")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    name, only = sys.argv[1], set(sys.argv[2:])
    with open(SHEET, encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["assigned_to"].lower() == name.lower()]
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
