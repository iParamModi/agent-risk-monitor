"""Copies the labels YOU typed in a viewer file into data/external/agentrisk_recheck.csv.

  python scripts/import_agentrisk_labels.py <YourName> local_notes/agentrisk_<YourName>.txt
  python scripts/import_agentrisk_labels.py --cause <YourName> local_notes/agentrisk_cause_<YourName>.txt

For labellers who wrote their choice after "done:" in the saved output of show_agentrisk_recheck.py:
  [4/36] AR-109   (split: train, mixed domain)   done: FINANCIAL_LOSS
Only rows assigned to <YourName> are filled (other people's items in a shared file are skipped); every
value must be one of the row's options or CONFUSED, otherwise nothing is written. The labeller runs this, not an LLM
(CLAUDE.md section 6: labels come from the human).
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHEET = ROOT / "data" / "external" / "agentrisk_recheck.csv"
COLUMN = "recheck_type"
HEADER = re.compile(r"^\[\d+/\d+\] (AR-\d+)\s.*\bdone: (.*?)\s*$")


def read_labels(text: str) -> dict[str, str]:
    """{record_id: label} from the item headers; '-' or empty means not labelled."""
    out = {}
    for line in text.splitlines():
        m = HEADER.match(line)
        if m and m.group(2) not in ("", "-"):
            out[m.group(1)] = m.group(2).strip()
    return out


def apply(rows: list[dict], name: str, labels: dict[str, str]) -> tuple[list[str], int]:
    """Fills rows in place; returns (problems, skipped other people's items). Problems: write nothing."""
    by_id = {r["record_id"]: r for r in rows}
    problems, skipped = [], 0
    for rid, label in labels.items():
        row = by_id.get(rid)
        if row is None:
            problems.append(f"{rid}: not in the sheet")
        elif row["assigned_to"] != name:
            skipped += 1
        elif row[COLUMN].strip() and row[COLUMN].strip() != label:
            problems.append(f"{rid}: sheet already has {row[COLUMN]!r}")
        elif label not in row["options"].split(" | ") + ["CONFUSED"]:
            problems.append(f"{rid}: {label!r} is not one of {row['options']} or CONFUSED")
        else:
            row[COLUMN] = label
    return problems, skipped


def main() -> int:
    global SHEET, COLUMN
    if "--cause" in sys.argv:
        sys.argv.remove("--cause")
        SHEET, COLUMN = ROOT / "data" / "external" / "agentrisk_cause_recheck.csv", "recheck_cause"
    if len(sys.argv) != 3:
        print(__doc__)
        return 1
    name, viewer_file = sys.argv[1], Path(sys.argv[2])
    labels = read_labels(viewer_file.read_text(encoding="utf-8"))
    with open(SHEET, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    problems, skipped = apply(rows, name, labels)
    if problems:
        print("nothing written:\n  " + "\n  ".join(problems))
        return 1
    with open(SHEET, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    mine = [r for r in rows if r["assigned_to"] == name]
    print(f"copied {len(labels) - skipped} labels ({skipped} of other people's items skipped); "
          f"{name}: {sum(bool(r[COLUMN].strip()) for r in mine)}/{len(mine)} filled")
    return 0


if __name__ == "__main__":
    sys.exit(main())
