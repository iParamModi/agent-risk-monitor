"""Risk types by hand for the UNSAFE train records that have none yet (now that Phase A uses the full train split).

  python scripts/make_untyped_recheck.py <Name>                       add rows + write local_notes/untyped_recheck_<Name>.txt
  python scripts/make_untyped_recheck.py --import <Name> <txt file>   copy the labels typed after "done:" into the sheets

Which records (58 on 2026-10-26):
  R-Judge  UNSAFE train records with no human type (outside the 300-sample, so never on the re-check sheet)
           -> new rows in data/external/risk_type_recheck.csv
  ATBench  UNSAFE records of the mixed harm info_ecosystem_and_societal_harm without a per-record label (R3.6)
           -> new rows in data/external/atbench_h5_recheck.csv
The txt file holds only the records: each record's visible conversation, the source's own description and
the options (the guide is data/external/risk_type_categories.txt). It shows no current or suggested type,
so the labelling stays blind. Labels come from the human only, no LLM (CLAUDE.md section 6); map_risk applies them.
"""
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.common.io import REPO_ROOT, read_jsonl  # noqa: E402
from src.external.map_risk import RISK_TYPES, load_atbench_recheck, load_human_types  # noqa: E402
from src.external.sample import MIXED_HARM  # noqa: E402

EXT = REPO_ROOT / "data" / "external"
SHEETS = {   # source -> (sheet, description column)
    "r_judge": (EXT / "risk_type_recheck.csv", "risk_description"),
    "atbench": (EXT / "atbench_h5_recheck.csv", "atbench_reason"),
}
OPTIONS = ["DATA_LOSS", "PRIVACY_LEAKAGE", "FINANCIAL_LOSS", "ACCESS_CONTROL", "SECURITY", "OTHER"]
MAX_TOOL_CHARS = 2000
HEADER = re.compile(r"^\[\d+/\d+\] ((?:RJ|ATB)-\S+)\s.*\bdone: (.*?)\s*$")


def untyped() -> dict[str, list[dict]]:
    human = load_human_types()
    atb_types, atb_confused = load_atbench_recheck()
    rj = [r for r in read_jsonl(EXT / "r_judge.jsonl")
          if r["gold"]["risk_label"] == "UNSAFE" and r["record_id"] not in human]
    atb = [r for r in read_jsonl(EXT / "atbench.jsonl")
           if r["gold"]["risk_label"] == "UNSAFE" and r["gold"]["source_taxonomy"]["real_world_harm"] == MIXED_HARM
           and r["record_id"] not in atb_types and r["record_id"] not in atb_confused]
    return {"r_judge": rj, "atbench": atb}


def read_sheet(path: Path) -> tuple[list[str], list[dict]]:
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames), list(reader)


def write_sheet(path: Path, columns: list[str], rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def add_rows(records: dict[str, list[dict]], name: str) -> dict[str, int]:
    added = {}
    for source, recs in records.items():
        path, desc = SHEETS[source]
        columns, rows = read_sheet(path)
        have = {r["record_id"] for r in rows}
        new = [{"record_id": r["record_id"], "assigned_to": name, "split": r["split"], desc: r["gold"]["source_note"] or "",
                "recheck_type": "", "recheck_note": ""} for r in recs if r["record_id"] not in have]
        if new:
            write_sheet(path, columns, rows + new)
        added[source] = len(new)
    return added


def render(rec: dict, n: int, total: int, name: str) -> str:
    source = "R-Judge" if rec["source"] == "r_judge" else "ATBench"
    out = ["=" * 80,
           f"[{n}/{total}] {rec['record_id']}   ({source}, split: {rec['split']})   for: {name}   done: -",
           "=" * 80]
    for step in rec["visible"]["trajectory"]:
        out.append(f"\n--- {step['role']} ---")
        text = step.get("text") or ""
        if step["role"] == "tool" and len(text) > MAX_TOOL_CHARS:
            text = text[:MAX_TOOL_CHARS] + f"\n... [{len(text) - MAX_TOOL_CHARS} more characters cut]"
        if text:
            out.append(text)
        if step.get("action_text"):
            out.append(f"ACTION: {step['action_text']}")
        if step.get("tool_call"):
            out.append(f"TOOL CALL: {json.dumps(step['tool_call'], ensure_ascii=False)}")
    out.append(f"\n{source} description: {rec['gold']['source_note'] or '-'}")
    out.append(f">>> CHOOSE ONE OF: {' | '.join(OPTIONS)}   (or CONFUSED)\n")
    return "\n".join(out)


def make(name: str) -> int:
    records = untyped()
    added = add_rows(records, name)
    ordered = sorted(records["r_judge"], key=lambda r: r["record_id"]) + sorted(records["atbench"], key=lambda r: r["record_id"])
    out = REPO_ROOT / "local_notes" / f"untyped_recheck_{name}.txt"
    if out.exists() and HEADER.search(out.read_text(encoding="utf-8")) and any(
            m.group(2) not in ("", "-") for m in map(HEADER.match, out.read_text(encoding="utf-8").splitlines()) if m):
        print(f"{out} already has labels; not overwriting")
        return 1
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n\n".join(render(r, i, len(ordered), name) for i, r in enumerate(ordered, 1)) + "\n",
                   encoding="utf-8")
    print(f"{len(ordered)} records (R-Judge {len(records['r_judge'])}, ATBench {len(records['atbench'])}); "
          f"rows added: R-Judge {added['r_judge']}, ATBench {added['atbench']}; file: {out.relative_to(REPO_ROOT)}")
    return 0


def read_labels(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        m = HEADER.match(line)
        if m and m.group(2) not in ("", "-"):
            out[m.group(1)] = m.group(2).strip()
    return out


def import_labels(name: str, path: Path) -> int:
    labels = read_labels(path.read_text(encoding="utf-8"))
    todo = {r["record_id"] for recs in untyped().values() for r in recs}     # before writing: afterwards they are typed
    problems, updates = [], {}
    for source, (sheet, _) in SHEETS.items():
        columns, rows = read_sheet(sheet)
        by_id = {r["record_id"]: r for r in rows}
        for rid, label in labels.items():
            row = by_id.get(rid)
            if row is None or row["assigned_to"] != name:
                continue
            if label not in OPTIONS + ["CONFUSED"]:
                problems.append(f"{rid}: {label!r} is not one of {OPTIONS} or CONFUSED")
            elif row["recheck_type"].strip() and row["recheck_type"].strip() != label:
                problems.append(f"{rid}: sheet already has {row['recheck_type']!r}")
            else:
                row["recheck_type"] = label
        updates[sheet] = (columns, rows)
    known = {r["record_id"] for _, rows in updates.values() for r in rows}
    problems += [f"{rid}: not in the sheets" for rid in labels if rid not in known]
    if problems:
        print("nothing written:\n  " + "\n  ".join(problems))
        return 1
    for sheet, (columns, rows) in updates.items():
        write_sheet(sheet, columns, rows)
    filled = sum(rid in labels for rid in todo)
    print(f"copied {len(labels)} labels; {filled}/{len(todo)} of the untyped records labelled. Next: python -m src.external.map_risk")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if args[:1] == ["--import"] and len(args) == 3:
        return import_labels(args[1], Path(args[2]))
    if len(args) == 1 and not args[0].startswith("-"):
        return make(args[0])
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
