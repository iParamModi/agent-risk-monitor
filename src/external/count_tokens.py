"""Fills meta.n_tokens for the external records (DATASET.md section 2.4, step 3).

Run: python -m src.external.count_tokens   (after src.external.map_risk; needs `tokenizers`)
Writes meta.n_tokens into data/external/<name>.jsonl and the per-record files, and a length
report to data/external/token_report.json: per split, and how many records pass each
training length (PLAN Step 17: 8,192 if memory allows, else 4,096).
"""
import statistics
import sys

from src.common.io import REPO_ROOT, read_jsonl, write_json, write_jsonl, write_record_files
from src.common.schema import schema_errors
from src.common.tokens import TOKENIZER_REPO, TOKENIZER_REVISION, count_tokens, load_tokenizer

EXT_DIR = REPO_ROOT / "data" / "external"
SPLIT_DIR = EXT_DIR / "splits"
REPORT = EXT_DIR / "token_report.json"
DATASETS = ("r_judge", "atbench")
LIMITS = (2048, 4096, 8192)


def length_stats(counts: list[int]) -> dict:
    if not counts:
        return {"records": 0}
    s = sorted(counts)
    return {
        "records": len(s), "mean": round(statistics.mean(s)), "median": round(statistics.median(s)),
        "p90": s[int(0.9 * (len(s) - 1))], "p95": s[int(0.95 * (len(s) - 1))], "max": s[-1],
        "over": {str(n): sum(c > n for c in s) for n in LIMITS},
    }


def report_for(records: list[dict], name: str) -> dict:
    n_tokens = {r["record_id"]: r["meta"]["n_tokens"] for r in records}
    parts = {"all": list(n_tokens)}
    for part in ("train", "train_sample300", "val", "test"):
        parts[part] = (SPLIT_DIR / f"{name}_{part}.txt").read_text(encoding="utf-8").split()
    out = {part: length_stats([n_tokens[i] for i in ids]) for part, ids in parts.items()}
    longest = sorted(records, key=lambda r: -r["meta"]["n_tokens"])[:5]
    out["longest"] = [{"record_id": r["record_id"], "n_tokens": r["meta"]["n_tokens"]} for r in longest]
    return out


def main() -> int:
    tokenizer = load_tokenizer()
    report = {"tokenizer": {"repo": TOKENIZER_REPO, "revision": TOKENIZER_REVISION},
              "counts": "visible part only (src/common/tokens.py render_visible); prompt template not included"}
    for name in DATASETS:
        records = list(read_jsonl(EXT_DIR / f"{name}.jsonl"))
        for rec in records:
            rec["meta"]["n_tokens"] = count_tokens(rec, tokenizer)
            errors = schema_errors(rec)
            if errors:
                raise ValueError(f"{rec['record_id']}: {errors}")
        write_jsonl(EXT_DIR / f"{name}.jsonl", records)
        write_record_files(EXT_DIR / name, records)
        report[name] = report_for(records, name)
        st = report[name]["all"]
        print(f"{name}: {st['records']} records, mean {st['mean']}, median {st['median']}, p95 {st['p95']}, "
              f"max {st['max']} tokens | over 4,096: {st['over']['4096']}, over 8,192: {st['over']['8192']}")
    write_json(REPORT, report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
