"""Shows your ATBench misinformation-harm re-check records WITHOUT any label, so the re-check stays blind.

Run: python scripts/show_atbench_recheck.py <YourName>             (all your rows)
     python scripts/show_atbench_recheck.py <YourName> ATB-123     (one record)
Covers the 25 used UNSAFE ATBench records whose real_world_harm is info_ecosystem_and_societal_harm
(decisions.md R3.6). Prints the visible trajectory + ATBench's reason only. Do not open the record JSON
files directly: their gold.risk_type holds the current label. Labels are typed by hand into
data/external/atbench_h5_recheck.csv with data/external/risk_type_categories.txt; no LLM may suggest
or fill them (see CLAUDE.md section 6).
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHEET = ROOT / "data" / "external" / "atbench_h5_recheck.csv"
RECORDS = ROOT / "data" / "external" / "atbench"
MAX_TOOL_CHARS = 2000   # ATBench tool outputs can be very long


def show(row: dict, n: int, total: int) -> None:
    rec = json.loads((RECORDS / f"{row['record_id']}.json").read_text(encoding="utf-8"))
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
        if step.get("tool_call"):
            print(f"TOOL CALL: {json.dumps(step['tool_call'], ensure_ascii=False)}")
    print(f"\nATBench reason: {row['atbench_reason']}\n")


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
