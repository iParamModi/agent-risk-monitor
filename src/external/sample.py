"""70/10/20 split by scenario + balanced 300 sample (DATASET.md section 2.3).

Run: python -m src.external.sample   (after src.external.normalize)
- Reads ALL normalized records from data/generated/normalized/, so the split never depends on exclusions.
- Groups (seed_id) never cross splits: R-Judge = file, ATBench = tool set.
- Groups are shuffled with seed 42, 43, ... until every split is within +-5 points of the
  dataset's unsafe rate; the seed that worked is saved in splits/split_report.json.
- From train: 150 SAFE + 150 UNSAFE, spread as evenly as possible over strata
  (R-Judge: category folder; ATBench unsafe: our risk_type, from the signed map + per-record labels;
  Meet 2026-10-26, was risk_source). ATBench records of the mixed harm (R3.6) without a per-record
  label are never sampled.
- Records listed in data/external/excluded_physical.txt are dropped AFTER the split; excluded members of
  the train sample are swapped for other train records with the same label and stratum.
Writes data/external/<name>.jsonl, the per-record files and the ID lists in data/external/splits/.
"""
import random
import sys
from collections import Counter, defaultdict
from typing import Callable

from src.common.io import REPO_ROOT, read_jsonl, write_json, write_jsonl, write_record_files
from src.common.schema import schema_errors
from src.external.map_risk import atbench_risk_type, load_atbench_recheck, load_map

EXT_DIR = REPO_ROOT / "data" / "external"
NORMALIZED_DIR = REPO_ROOT / "data" / "generated" / "normalized"
EXCLUDED_FILE = EXT_DIR / "excluded_physical.txt"
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


def stratified_sample(pool: list[dict], n: int, stratum: Callable[[dict], str | None], rng: random.Random) -> list[dict]:
    """Stratum None = not eligible for the sample."""
    by = defaultdict(list)
    for r in sorted(pool, key=lambda r: r["record_id"]):
        if (k := stratum(r)) is not None:
            by[k].append(r)
    take = even_allocation({k: len(v) for k, v in by.items()}, n)
    return [r for k in sorted(by) for r in rng.sample(by[k], take[k])]


def sample_train(train: list[dict], seed: int, safe_stratum, unsafe_stratum, per_class: int = PER_CLASS) -> list[dict]:
    rng = random.Random(seed)
    safe = stratified_sample([r for r in train if not is_unsafe(r)], per_class, safe_stratum, rng)
    unsafe = stratified_sample([r for r in train if is_unsafe(r)], per_class, unsafe_stratum, rng)
    return sorted(safe + unsafe, key=lambda r: r["record_id"])


def rjudge_stratum(rec: dict) -> str:
    return rec["meta"]["category"]


MIXED_HARM = "info_ecosystem_and_societal_harm"     # R3.6: typed one by one (atbench_h5_recheck.csv)


def atbench_type_stratum() -> Callable[[dict], str | None]:
    """Our risk_type of an UNSAFE ATBench record, as map_risk will set it; None if it has no final type."""
    m = load_map()
    human, confused = load_atbench_recheck()

    def stratum(rec: dict) -> str | None:
        rid = rec["record_id"]
        if rid in confused or (rec["gold"]["source_taxonomy"]["real_world_harm"] == MIXED_HARM and rid not in human):
            return None
        return human.get(rid) or atbench_risk_type(rec, m)
    return stratum


DATASETS = {
    # name: (stratum for SAFE, stratum for UNSAFE); a function returning one makes it when the step runs
    "r_judge": (lambda: rjudge_stratum, lambda: rjudge_stratum),
    "atbench": (lambda: (lambda r: "all"), atbench_type_stratum),
}


def load_excluded(path=EXCLUDED_FILE) -> set[str]:
    """record_ids, one per line; '#' starts a comment."""
    if not path.exists():
        return set()
    return {line.split("#")[0].strip() for line in path.read_text(encoding="utf-8").splitlines()} - {""}


def replace_excluded(sample: list[dict], train: list[dict], excluded: set[str], safe_stratum, unsafe_stratum,
                     seed: int) -> tuple[list[dict], list[tuple[str, str]]]:
    """Swap each excluded sample member for an unused train record with the same label (same stratum if possible).
    Everything else in the sample stays as it was, so earlier human labels remain valid."""
    rng = random.Random(seed + 1)
    in_sample = {r["record_id"] for r in sample}
    pool = sorted((r for r in train if r["record_id"] not in in_sample and r["record_id"] not in excluded),
                  key=lambda r: r["record_id"])
    kept, swaps = [], []
    for r in sorted(sample, key=lambda r: r["record_id"]):
        if r["record_id"] not in excluded:
            kept.append(r)
            continue
        stratum = unsafe_stratum if is_unsafe(r) else safe_stratum
        same_label = [c for c in pool if is_unsafe(c) == is_unsafe(r)
                      and (unsafe_stratum if is_unsafe(c) else safe_stratum)(c) is not None]
        same_stratum = [c for c in same_label if stratum(c) == stratum(r)]
        choices = same_stratum or same_label
        if not choices:
            raise ValueError(f"no replacement left for {r['record_id']}")
        new = rng.choice(choices)
        pool.remove(new)
        kept.append(new)
        swaps.append((r["record_id"], new["record_id"]))
    return sorted(kept, key=lambda r: r["record_id"]), swaps


def write_ids(path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(r["record_id"] + "\n" for r in sorted(records, key=lambda r: r["record_id"])),
                    encoding="utf-8")


def process(name: str, excluded: set[str]) -> dict:
    records = list(read_jsonl(NORMALIZED_DIR / f"{name}.jsonl"))
    seed, where, stats = find_split(records)
    for r in records:
        r["split"] = where[r["seed_id"]]
        errors = schema_errors(r)
        if errors:
            raise ValueError(f"{r['record_id']}: {errors}")
    safe_stratum, unsafe_stratum = (make() for make in DATASETS[name])
    train = [r for r in records if r["split"] == "train"]
    sample = sample_train(train, seed, safe_stratum, unsafe_stratum)
    sample, swaps = replace_excluded(sample, train, excluded, safe_stratum, unsafe_stratum, seed)

    dropped = [r for r in records if r["record_id"] in excluded]
    records = [r for r in records if r["record_id"] not in excluded]
    write_jsonl(EXT_DIR / f"{name}.jsonl", records)
    write_record_files(EXT_DIR / name, records)
    for s in FRACTIONS:
        write_ids(SPLIT_DIR / f"{name}_{s}.txt", [r for r in records if r["split"] == s])
    write_ids(SPLIT_DIR / f"{name}_train_sample300.txt", sample)

    return {
        "seed": seed,
        "overall_unsafe_rate": round(sum(map(is_unsafe, records)) / len(records), 4),
        "splits_before_exclusion": stats,
        "splits": split_stats(records, where),
        "excluded": {"records": len(dropped), "by_split": dict(Counter(r["split"] for r in dropped)),
                     "sample_swaps": [{"out": a, "in": b} for a, b in swaps]},
        "train_sample": {
            "records": len(sample), "safe": sum(not is_unsafe(r) for r in sample),
            "unsafe": sum(map(is_unsafe, sample)),
            "safe_by_stratum": dict(sorted(Counter(safe_stratum(r) for r in sample if not is_unsafe(r)).items())),
            "unsafe_by_stratum": dict(sorted(Counter(unsafe_stratum(r) for r in sample if is_unsafe(r)).items())),
        },
        "groups": {s: sorted({g for g, w in where.items() if w == s}) for s in FRACTIONS} if name == "r_judge" else None,
    }


def main() -> int:
    excluded = load_excluded()
    report = {name: process(name, excluded) for name in DATASETS}
    report["settings"] = {"fractions": FRACTIONS, "max_overfill": MAX_OVERFILL, "balance_pp": BALANCE_PP,
                          "first_seed": FIRST_SEED, "per_class": PER_CLASS}
    write_json(SPLIT_DIR / "split_report.json", report)
    for name in DATASETS:
        r = report[name]
        parts = ", ".join(f"{s} {st['records']} ({st['unsafe_rate']:.1%} unsafe, {st['groups']} groups)"
                          for s, st in r["splits"].items())
        print(f"{name}: seed {r['seed']} | {parts} | sample {r['train_sample']['safe']}+{r['train_sample']['unsafe']}"
              f" | excluded {r['excluded']['records']} ({len(r['excluded']['sample_swaps'])} swapped in sample)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
