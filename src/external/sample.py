"""70/10/20 split by scenario + balanced 300 sample (DATASET.md section 2.3).

Run: python -m src.external.sample   (after src.external.normalize)
- Groups (seed_id) never cross splits: R-Judge = file, ATBench = tool set.
- Groups are shuffled with seed 42, 43, ... until every split is within +-5 points of the
  dataset's unsafe rate; the seed that worked is saved in splits/split_report.json.
- From train: 150 SAFE + 150 UNSAFE, spread as evenly as possible over strata
  (R-Judge: category folder; ATBench unsafe: risk_source).
Fills record["split"] in data/external/<name>.jsonl and the per-record files; writes ID lists
to data/external/splits/.
"""
import random
import sys
from collections import Counter, defaultdict
from typing import Callable

from src.common.io import REPO_ROOT, read_jsonl, write_json, write_jsonl, write_record_files
from src.common.schema import schema_errors

EXT_DIR = REPO_ROOT / "data" / "external"
SPLIT_DIR = EXT_DIR / "splits"
FRACTIONS = {"train": 0.7, "val": 0.1, "test": 0.2}
MAX_OVERFILL = 0.15      # a group may push val/test at most 15% past its target size
BALANCE_PP = 0.05        # each split's unsafe rate within +-5 points of the whole dataset
FIRST_SEED, MAX_TRIES = 42, 1000
PER_CLASS = 150


def is_unsafe(rec: dict) -> bool:
    return rec["gold"]["risk_label"] == "UNSAFE"


def assign_groups(records: list[dict], seed: int) -> dict[str, str]:
    """Shuffle groups; fill test, then val, up to their target size; the rest go to train."""
    sizes = Counter(r["seed_id"] for r in records)
    total = len(records)
    target = {s: FRACTIONS[s] * total for s in ("test", "val")}
    filled = {"test": 0, "val": 0}
    groups = sorted(sizes)
    random.Random(seed).shuffle(groups)
    where = {}
    for g in groups:
        where[g] = "train"
        for s in ("test", "val"):
            if filled[s] < target[s] and filled[s] + sizes[g] <= target[s] * (1 + MAX_OVERFILL):
                where[g] = s
                filled[s] += sizes[g]
                break
    return where


def split_stats(records: list[dict], where: dict[str, str]) -> dict:
    stats = {}
    for s in FRACTIONS:
        part = [r for r in records if where[r["seed_id"]] == s]
        unsafe = sum(map(is_unsafe, part))
        stats[s] = {"records": len(part), "safe": len(part) - unsafe, "unsafe": unsafe,
                    "unsafe_rate": round(unsafe / len(part), 4) if part else None,
                    "groups": len({r["seed_id"] for r in part})}
    return stats


def is_acceptable(records: list[dict], stats: dict, per_class: int) -> bool:
    overall = sum(map(is_unsafe, records)) / len(records)
    if any(st["records"] == 0 or abs(st["unsafe_rate"] - overall) > BALANCE_PP for st in stats.values()):
        return False
    return stats["train"]["safe"] >= per_class and stats["train"]["unsafe"] >= per_class


def find_split(records: list[dict], per_class: int = PER_CLASS) -> tuple[int, dict[str, str], dict]:
    for seed in range(FIRST_SEED, FIRST_SEED + MAX_TRIES):
        where = assign_groups(records, seed)
        stats = split_stats(records, where)
        if is_acceptable(records, stats, per_class):
            return seed, where, stats
    raise RuntimeError(f"no seed in {FIRST_SEED}..{FIRST_SEED + MAX_TRIES - 1} gives a balanced split")


def even_allocation(available: dict[str, int], n: int) -> dict[str, int]:
    """Split n over strata as evenly as possible, never taking more than a stratum has."""
    if sum(available.values()) < n:
        raise ValueError(f"need {n}, only {sum(available.values())} available")
    take = {k: 0 for k in available}
    left = n
    while left:
        open_ = sorted(k for k in available if take[k] < available[k])
        share, extra = divmod(left, len(open_))
        for i, k in enumerate(open_):
            add = min(share + (1 if i < extra else 0), available[k] - take[k])
            take[k] += add
            left -= add
    return take


def stratified_sample(pool: list[dict], n: int, stratum: Callable[[dict], str], rng: random.Random) -> list[dict]:
    by = defaultdict(list)
    for r in sorted(pool, key=lambda r: r["record_id"]):
        by[stratum(r)].append(r)
    take = even_allocation({k: len(v) for k, v in by.items()}, n)
    return [r for k in sorted(by) for r in rng.sample(by[k], take[k])]


def sample_train(train: list[dict], seed: int, safe_stratum, unsafe_stratum, per_class: int = PER_CLASS) -> list[dict]:
    rng = random.Random(seed)
    safe = stratified_sample([r for r in train if not is_unsafe(r)], per_class, safe_stratum, rng)
    unsafe = stratified_sample([r for r in train if is_unsafe(r)], per_class, unsafe_stratum, rng)
    return sorted(safe + unsafe, key=lambda r: r["record_id"])


def rjudge_stratum(rec: dict) -> str:
    return rec["meta"]["category"]


def atbench_unsafe_stratum(rec: dict) -> str:
    return rec["gold"]["source_taxonomy"]["risk_source"]


DATASETS = {
    # name: (stratum for SAFE, stratum for UNSAFE)
    "r_judge": (rjudge_stratum, rjudge_stratum),
    "atbench": (lambda r: "all", atbench_unsafe_stratum),
}


def write_ids(path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(r["record_id"] + "\n" for r in sorted(records, key=lambda r: r["record_id"])),
                    encoding="utf-8")


def process(name: str) -> dict:
    records = list(read_jsonl(EXT_DIR / f"{name}.jsonl"))
    seed, where, stats = find_split(records)
    for r in records:
        r["split"] = where[r["seed_id"]]
        errors = schema_errors(r)
        if errors:
            raise ValueError(f"{r['record_id']}: {errors}")
    safe_stratum, unsafe_stratum = DATASETS[name]
    train = [r for r in records if r["split"] == "train"]
    sample = sample_train(train, seed, safe_stratum, unsafe_stratum)

    write_jsonl(EXT_DIR / f"{name}.jsonl", records)
    write_record_files(EXT_DIR / name, records)
    for s in FRACTIONS:
        write_ids(SPLIT_DIR / f"{name}_{s}.txt", [r for r in records if r["split"] == s])
    write_ids(SPLIT_DIR / f"{name}_train_sample300.txt", sample)

    return {
        "seed": seed,
        "overall_unsafe_rate": round(sum(map(is_unsafe, records)) / len(records), 4),
        "splits": stats,
        "train_sample": {
            "records": len(sample), "safe": sum(not is_unsafe(r) for r in sample),
            "unsafe": sum(map(is_unsafe, sample)),
            "safe_by_stratum": dict(sorted(Counter(safe_stratum(r) for r in sample if not is_unsafe(r)).items())),
            "unsafe_by_stratum": dict(sorted(Counter(unsafe_stratum(r) for r in sample if is_unsafe(r)).items())),
        },
        "groups": {s: sorted({g for g, w in where.items() if w == s}) for s in FRACTIONS} if name == "r_judge" else None,
    }


def main() -> int:
    report = {name: process(name) for name in DATASETS}
    report["settings"] = {"fractions": FRACTIONS, "max_overfill": MAX_OVERFILL, "balance_pp": BALANCE_PP,
                          "first_seed": FIRST_SEED, "per_class": PER_CLASS}
    write_json(SPLIT_DIR / "split_report.json", report)
    for name in DATASETS:
        r = report[name]
        parts = ", ".join(f"{s} {st['records']} ({st['unsafe_rate']:.1%} unsafe, {st['groups']} groups)"
                          for s, st in r["splits"].items())
        print(f"{name}: seed {r['seed']} | {parts} | sample {r['train_sample']['safe']}+{r['train_sample']['unsafe']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
