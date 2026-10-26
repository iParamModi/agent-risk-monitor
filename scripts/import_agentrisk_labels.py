"""Copies the labels YOU typed in a viewer file into data/external/agentrisk_recheck.csv.

  python scripts/import_agentrisk_labels.py <YourName> local_notes/agentrisk_<YourName>.txt

For labellers who wrote their choice after "done:" in the saved output of show_agentrisk_recheck.py:
  [4/36] AR-109   (split: train, mixed domain)   done: FINANCIAL_LOSS
Only rows assigned to <YourName> with an empty recheck_type are filled; every value must be one of the
row's options or CONFUSED, otherwise nothing is written. The labeller runs this, not an LLM
(CLAUDE.md section 6: labels come from the human).
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHEET = ROOT / "data" / "external" / "agentrisk_recheck.csv"
HEADER = re.compile(r"^\[\d+/\d+\] (AR-\d+)\s.*\bdone: (.*?)\s*$")


def read_labels(text: str) -> dict[str, str]:
    """{record_id: label} from the item headers; '-' or empty means not labelled."""
    out = {}
    for line in text.splitlines():
        m = HEADER.match(line)
        if m and m.group(2) not in ("", "-"):
            out[m.group(1)] = m.group(2).strip()
    return out


def apply(rows: list[dict], name: str, labels: dict[str, str]) -> list[str]:
    """Fills rows in place; returns problems (then nothing should be written)."""
    by_id = {r["record_id"]: r for r in rows}
    problems = []
    for rid, label in labels.items():
        row = by_id.get(rid)
        if row is None:
            problems.append(f"{rid}: not in the sheet")
        elif row["assigned_to"] != name:
            problems.append(f"{rid}: assigned to {row['assigned_to']}, not {name}")
        elif row["recheck_type"].strip() and row["recheck_type"].strip() != label:
            problems.append(f"{rid}: sheet already has {row['recheck_type']!r}")
        elif label not in row["options"].split(" | ") + ["CONFUSED"]:
            problems.append(f"{rid}: {label!r} is not one of {row['options']} or CONFUSED")
        else:
            row["recheck_type"] = label
    return problems


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    name, viewer_file = sys.argv[1], Path(sys.argv[2])
    labels = read_labels(viewer_file.read_text(encoding="utf-8"))
    with open(SHEET, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    problems = apply(rows, name, labels)
    if problems:
        print("nothing written:\n  " + "\n  ".join(problems))
        return 1
    with open(SHEET, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    mine = [r for r in rows if r["assigned_to"] == name]
    print(f"copied {len(labels)} labels; {name}: {sum(bool(r['recheck_type'].strip()) for r in mine)}/{len(mine)} filled")
    return 0


if __name__ == "__main__":
    sys.exit(main())
