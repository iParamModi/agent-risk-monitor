"""Risk-type mapping + LLM suggestions (DATASET.md section 2.5).

Run: python -m src.external.map_risk   (after src.external.sample)
ATBench: fills gold.risk_type for UNSAFE records from data/external/risk_type_map.yaml.
R-Judge: not done yet (LLM suggests, human decides in risk_type_review.csv).
"""
import sys
from collections import Counter

import yaml

from src.common.io import REPO_ROOT, read_jsonl, write_jsonl, write_record_files
from src.common.schema import schema_errors

EXT_DIR = REPO_ROOT / "data" / "external"
MAP_FILE = EXT_DIR / "risk_type_map.yaml"
RISK_TYPES = {"DATA_LOSS", "PRIVACY_LEAKAGE", "FINANCIAL_LOSS", "ACCESS_CONTROL", "SECURITY", "OTHER"}


def load_map(path=MAP_FILE) -> dict:
    m = yaml.safe_load(path.read_text(encoding="utf-8"))
    m.setdefault("failure_mode_overrides_for_other", {})
    m["record_overrides"] = m.get("record_overrides") or {}
    used = (set(m["harm_to_type"].values()) | set(m["failure_mode_overrides_for_other"].values())
            | set(m["record_overrides"].values()))
    if used - RISK_TYPES:
        raise ValueError(f"unknown risk types in {path.name}: {sorted(used - RISK_TYPES)}")
    return m


def atbench_risk_type(rec: dict, m: dict) -> str:
    """record override > harm map > failure_mode rule (only when the harm maps to OTHER)."""
    if rec["record_id"] in m["record_overrides"]:
        return m["record_overrides"][rec["record_id"]]
    tax = rec["gold"]["source_taxonomy"]
    harm = tax["real_world_harm"]
    if harm not in m["harm_to_type"]:
        raise KeyError(f"{rec['record_id']}: harm {harm!r} missing from {MAP_FILE.name}")
    risk_type = m["harm_to_type"][harm]
    if risk_type == "OTHER":
        risk_type = m["failure_mode_overrides_for_other"].get(tax["failure_mode"], risk_type)
    return risk_type


def map_atbench(records: list[dict], m: dict) -> Counter:
    counts = Counter()
    for rec in records:
        if rec["gold"]["risk_label"] == "UNSAFE":
            rec["gold"]["risk_type"] = atbench_risk_type(rec, m)
            counts[rec["gold"]["risk_type"]] += 1
        errors = schema_errors(rec)
        if errors:
            raise ValueError(f"{rec['record_id']}: {errors}")
    return counts


def main() -> int:
    records = list(read_jsonl(EXT_DIR / "atbench.jsonl"))
    counts = map_atbench(records, load_map())
    write_jsonl(EXT_DIR / "atbench.jsonl", records)
    write_record_files(EXT_DIR / "atbench", records)
    total = sum(counts.values())
    print(f"atbench: risk_type set for {total} unsafe records")
    for t, n in counts.most_common():
        print(f"  {t:<16} {n:>4}  ({n / total:.1%})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
