"""Risk-type mapping + LLM suggestions (DATASET.md section 2.5).

Run: python -m src.external.map_risk   (after src.external.sample)
ATBench: fills gold.risk_type for UNSAFE records from data/external/risk_type_map.yaml.
R-Judge: fills gold.risk_type for UNSAFE records from human labels: recheck_type in
data/external/risk_type_recheck.csv if filled, else human_final in risk_type_review.csv
(LLM suggests, humans decide; guide: risk_type_categories.txt). Used records still without a
human label are listed in the report.
Also writes data/labels/kappa_report.json: reviewer agreement on risk_type_double_check.csv.
"""
import csv
import sys
from collections import Counter

import yaml

from src.common.io import REPO_ROOT, read_jsonl, write_json, write_jsonl, write_record_files
from src.common.schema import schema_errors

EXT_DIR = REPO_ROOT / "data" / "external"
MAP_FILE = EXT_DIR / "risk_type_map.yaml"
REVIEW_FILE = EXT_DIR / "risk_type_review.csv"
RECHECK_FILE = EXT_DIR / "risk_type_recheck.csv"
DOUBLE_CHECK_FILE = EXT_DIR / "risk_type_double_check.csv"
KAPPA_REPORT = REPO_ROOT / "data" / "labels" / "kappa_report.json"
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


def read_csv(path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _checked(value: str, record_id: str, column: str) -> str:
    if value not in RISK_TYPES:
        raise ValueError(f"{record_id}: unknown {column} {value!r}")
    return value


def load_human_types(review=REVIEW_FILE, recheck=RECHECK_FILE) -> dict[str, str]:
    """Human risk types per record_id. A filled recheck_type overrides the first review."""
    types = {}
    for row in read_csv(review):
        if row["human_final"].strip():
            types[row["record_id"]] = _checked(row["human_final"].strip(), row["record_id"], "human_final")
    if recheck.exists():
        for row in read_csv(recheck):
            if row["recheck_type"].strip():
                types[row["record_id"]] = _checked(row["recheck_type"].strip(), row["record_id"], "recheck_type")
    return types


def map_rjudge(records: list[dict], human: dict[str, str], used: set[str]) -> tuple[Counter, list[str]]:
    """UNSAFE records get the human type; returns counts and the used UNSAFE ids still without one."""
    counts, missing = Counter(), []
    for rec in records:
        if rec["gold"]["risk_label"] != "UNSAFE":
            continue
        rec["gold"]["risk_type"] = human.get(rec["record_id"])
        if rec["gold"]["risk_type"]:
            counts[rec["gold"]["risk_type"]] += 1
        elif rec["record_id"] in used:
            missing.append(rec["record_id"])
        errors = schema_errors(rec)
        if errors:
            raise ValueError(f"{rec['record_id']}: {errors}")
    return counts, sorted(missing)


def cohen_kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb[k] for k in set(a) | set(b)) / (n * n)
    return 1.0 if expected == 1 else round((observed - expected) / (1 - expected), 4)


def rjudge_agreement(human: dict[str, str], present: set[str]) -> dict:
    rows = [r for r in read_csv(DOUBLE_CHECK_FILE) if r["reviewer_b_type"].strip()]
    pairs = [(human[r["record_id"]], r["reviewer_b_type"].strip()) for r in rows
             if r["record_id"] in human and r["record_id"] in present]
    if not pairs:
        return {"items": 0}
    a, b = zip(*pairs)
    return {"field": "risk_type", "reviewer_a": "risk_type_review.csv human_final", "reviewer_b": "risk_type_double_check.csv",
            "items": len(pairs), "dropped_excluded": len(rows) - len(pairs),
            "agreement": round(sum(x == y for x, y in pairs) / len(pairs), 4), "cohen_kappa": cohen_kappa(list(a), list(b)),
            "threshold": 0.6, "disagreements": [{"record_id": r["record_id"], "a": human[r["record_id"]], "b": r["reviewer_b_type"].strip()}
                                                for r in rows if r["record_id"] in present and r["record_id"] in human
                                                and human[r["record_id"]] != r["reviewer_b_type"].strip()]}


def used_ids(name: str) -> set[str]:
    split_dir = EXT_DIR / "splits"
    ids = set()
    for part in ("train_sample300", "val", "test"):
        ids |= set((split_dir / f"{name}_{part}.txt").read_text(encoding="utf-8").split())
    return ids


def show(name: str, counts: Counter) -> None:
    total = sum(counts.values())
    print(f"{name}: risk_type set for {total} unsafe records")
    for t, n in counts.most_common():
        print(f"  {t:<16} {n:>4}  ({n / total:.1%})")


def main() -> int:
    records = list(read_jsonl(EXT_DIR / "atbench.jsonl"))
    counts = map_atbench(records, load_map())
    write_jsonl(EXT_DIR / "atbench.jsonl", records)
    write_record_files(EXT_DIR / "atbench", records)
    show("atbench", counts)

    records = list(read_jsonl(EXT_DIR / "r_judge.jsonl"))
    human = load_human_types()
    counts, missing = map_rjudge(records, human, used_ids("r_judge"))
    write_jsonl(EXT_DIR / "r_judge.jsonl", records)
    write_record_files(EXT_DIR / "r_judge", records)
    show("r_judge", counts)
    if missing:
        print(f"  {len(missing)} used UNSAFE records still need a human type: {', '.join(missing)}")

    kappa = rjudge_agreement(human, {r["record_id"] for r in records})
    write_json(KAPPA_REPORT, {"r_judge_risk_type_double_check": kappa})
    if kappa.get("items"):
        print(f"r_judge double check: {kappa['items']} items, agreement {kappa['agreement']:.0%}, "
              f"Cohen's kappa {kappa['cohen_kappa']} (threshold 0.6)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
