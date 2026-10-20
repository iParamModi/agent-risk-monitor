"""Shows your R-Judge re-check records WITHOUT any label, so the re-check stays blind.

Run: python scripts/show_recheck.py <YourName>            (all your rows)
     python scripts/show_recheck.py <YourName> RJ-xxx-1   (one record)
Prints the visible trajectory + R-Judge's risk description only. Do not open the record JSON
files directly: their gold.risk_type holds the old label. Labels are typed by hand into
data/external/risk_type_recheck.csv; no LLM may suggest or fill them (see CLAUDE.md).
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHEET = ROOT / "data" / "external" / "risk_type_recheck.csv"
RECORDS = ROOT / "data" / "external" / "r_judge"


def show(row: dict, n: int, total: int) -> None:
    rec = json.loads((RECORDS / f"{row['record_id']}.json").read_text(encoding="utf-8"))
    print("=" * 80)
    print(f"[{n}/{total}] {row['record_id']}   (split: {row['split']})   done: {row['recheck_type'] or '-'}")
    print("=" * 80)
    for step in rec["visible"]["trajectory"]:
        print(f"\n--- {step['role']} ---")
        if step.get("text"):
            print(step["text"])
        if step.get("action_text"):
            print(f"ACTION: {step['action_text']}")
        if step.get("tool_call"):
            print(f"TOOL CALL: {json.dumps(step['tool_call'], ensure_ascii=False)}")
    print(f"\nR-Judge risk description: {row['risk_description']}\n")


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
