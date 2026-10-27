"""Read-only preview of gold.required_checks (seed_to_record.md D4): which check-needed records have a check tool.

For each record with gold.check_needed, every deciding fact in hidden.key_facts must have a tool in
configs/fact_checks.yaml that has a row for the record's action in configs/check_table.yaml (OOD-only tools on OOD
records only). Writes nothing into the records: filling required_checks is Param's task (HIGH PRIORITY #4).

Run:  python scripts/preview_required_checks.py
"""
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.common.io import read_jsonl  # noqa: E402

FACT_CHECKS = yaml.safe_load((ROOT / "configs" / "fact_checks.yaml").read_text(encoding="utf-8"))
TABLE = yaml.safe_load((ROOT / "configs" / "check_table.yaml").read_text(encoding="utf-8"))


def tools_for(fact: str, action: str, ood: bool) -> list[str]:
    row = {e["check"] for e in TABLE.get(action) or []}
    return [e["tool"] for e in FACT_CHECKS.get(fact, []) if e["tool"] in row and (ood or not e["ood"])]


def main():
    records = [r for n in ("all_in_domain", "all_ood") for r in read_jsonl(ROOT / "data" / "records" / f"{n}.jsonl")]
    need = [r for r in records if r["gold"]["check_needed"]]
    missing, why = [], Counter()
    for r in need:
        action = r["visible"]["proposed_action"]["name"]
        for key in r["hidden"]["key_facts"]:
            fact = key.rsplit(".", 1)[1]
            if not tools_for(fact, action, r["set"] == "ood"):
                missing.append((r["record_id"], fact, action))
                why[fact] += 1
    ids = sorted({m[0] for m in missing})
    print(f"check-needed records: {len(need)}; with a check for every deciding fact: {len(need) - len(ids)}; "
          f"without: {len(ids)}")
    for fact, n in why.most_common():
        print(f"  {fact}: {n} fact(s) in {sorted({m[0] for m in missing if m[1] == fact})}")


if __name__ == "__main__":
    main()
