"""Step 11: split our records by seed and lock the test files (PLAN Step 11, decisions.md R11.3).

    python -m src.data_gen.split [--relock]     (after src.data_gen.merge; make records runs both)

- In-domain seeds -> train / val / test at 60 / 10 / 30 (Meet, 2026-10-27: 162 seeds instead of the planned 150,
  and more training data for the Phase B fine-tune). All records of a seed (A/B, a-d, v1/v2) share its split.
- Seeds that share a gold policy, or whose prose is a near duplicate (dedup.py), form one group and get one
  split, so the same policy text never decides both a training case and a test case.
- Groups are placed largest first, each into the split whose counts per case type and per domain are furthest
  below their targets; ties go to train, then test, then val, and a fixed random order (seed 42) breaks size ties.
- The assignment is sticky: a seed already listed in data/records/splits.yaml keeps its split (and so does the
  rest of its group), so regenerating some records never moves seeds between train and test. Only new seeds
  are placed. --reassign starts from scratch (only on purpose, with a Changelog row). A group whose seeds are
  listed in two splits (e.g. a seed now shares a policy with a test seed) stops the split.
- All OOD records are test only (split = "test", file ood_test.jsonl).
- Writes the split into data/records/all_in_domain.jsonl and all_ood.jsonl, and writes train.jsonl, val.jsonl,
  test.jsonl, ood_test.jsonl and splits.yaml there; the report goes to data/generated/reports/split_report.json.
- Locks test.jsonl and ood_test.jsonl by SHA-256 in data/LOCKED_TEST.sha256 (tests/test_locked_test_set.py).
  If the lock exists and a test file would change, nothing is written unless --relock is given: a test-set
  change must be deliberate, with a Changelog row in docs/decisions.md.
"""
import argparse
import hashlib
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from src.common.io import REPO_ROOT, read_jsonl, write_json, write_jsonl
from src.common.seed import set_seed
from src.data_gen.dedup import similar_pairs

RECORDS = REPO_ROOT / "data" / "records"
REPORTS = REPO_ROOT / "data" / "generated" / "reports"
LOCK = REPO_ROOT / "data" / "LOCKED_TEST.sha256"
SPLITS = ("train", "val", "test")
RATIOS = {"train": 0.6, "val": 0.1, "test": 0.3}
TIE_ORDER = ("train", "test", "val")
SEED = 42
LOCKED_FILES = ("test.jsonl", "ood_test.jsonl")


def seed_groups(records: list[dict], near_duplicates: list[dict]) -> list[list[str]]:
    """Seed ids joined when they share a gold policy id or a near-duplicate record pair; sorted groups."""
    parent: dict[str, str] = {}

    def root(x: str) -> str:
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def join(a: str, b: str) -> None:
        parent[root(a)] = root(b)

    by_policy = defaultdict(set)
    for r in records:
        root(r["seed_id"])
        for pid in r["gold"]["policy_ids"]:
            by_policy[pid].add(r["seed_id"])
    for seeds in by_policy.values():
        first, *rest = sorted(seeds)
        for s in rest:
            join(first, s)
    seed_of = {r["record_id"]: r["seed_id"] for r in records}
    for pair in near_duplicates:
        join(seed_of[pair["a"]], seed_of[pair["b"]])
    groups = defaultdict(list)
    for s in sorted(parent):
        groups[root(s)].append(s)
    return sorted(groups.values())


class SplitConflict(ValueError):
    """A group of seeds that must share a split is already listed in two splits."""


def assign(groups: list[list[str]], seed_info: dict[str, tuple[str, str]], fixed: dict[str, str] | None = None,
           ratios: dict[str, float] = RATIOS, seed: int = SEED) -> dict[str, str]:
    """seed_id -> split. seed_info: seed_id -> (case_type, domain); fixed: seeds whose split is already decided
    (their whole group follows them). The other groups: greedy on the squared shortfall per case type, per domain
    and in total, each scaled by its size, so small domains count as much as large ones."""
    fixed = fixed or {}
    dims = lambda sids: Counter(d for s in sids for d in ("all", *seed_info[s]))   # noqa: E731
    totals = dims(seed_info)
    target = {sp: {d: ratios[sp] * n for d, n in totals.items()} for sp in SPLITS}
    have = {sp: Counter() for sp in SPLITS}
    out, free = {}, []
    for group in groups:
        decided = {fixed[s] for s in group if s in fixed}
        if len(decided) > 1:
            raise SplitConflict(f"seeds {group} must share a split but are listed in {sorted(decided)}")
        if decided:
            sp = decided.pop()
            have[sp].update(dims(group))
            out.update({s: sp for s in group})
        else:
            free.append(group)
    random.Random(seed).shuffle(free)
    free.sort(key=len, reverse=True)            # stable: the shuffle breaks ties between equal sizes

    def cost(sp: str, add: Counter) -> float:
        return sum(((have[sp][d] + n - target[sp][d]) ** 2 - (have[sp][d] - target[sp][d]) ** 2) / totals[d]
                   for d, n in add.items())

    for group in free:
        add = dims(group)
        best = min(TIE_ORDER, key=lambda sp: (round(cost(sp, add), 9), TIE_ORDER.index(sp)))
        have[best].update(add)
        out.update({s: best for s in group})
    return out


def listed_splits(path: Path = RECORDS / "splits.yaml") -> dict[str, str]:
    """seed_id -> split from an earlier run's splits.yaml (in-domain splits only); {} if there is none."""
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {sid: sp for sp in SPLITS for sid in raw.get(sp) or []}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_lock(path: Path = LOCK) -> dict[str, str]:
    """{relative path: sha256} from a sha256sum-style file."""
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            digest, rel = line.split(maxsplit=1)
            out[rel.strip()] = digest
    return out


def lock_text(hashes: dict[str, str]) -> str:
    return ("# SHA-256 of the locked test files (PLAN Step 11). Written by python -m src.data_gen.split;\n"
            "# change only on purpose, with a Changelog row in docs/decisions.md. Check: sha256sum -c\n"
            + "".join(f"{h}  {rel}\n" for rel, h in sorted(hashes.items())))


def counts(rows: list[dict]) -> dict:
    return {"seeds": len({r["seed_id"] for r in rows}), "records": len(rows),
            "case_type": dict(sorted(Counter(r["case_type"] for r in rows).items())),
            "domain": dict(sorted(Counter(r["domain"] for r in rows).items())),
            "decision": dict(sorted(Counter(r["gold"]["decision"] for r in rows).items())),
            "risk_type": dict(sorted(Counter(r["gold"]["risk_type"] for r in rows).items())),
            "check_needed": sum(r["gold"]["check_needed"] for r in rows)}


def split(in_domain: list[dict], ood: list[dict], fixed: dict[str, str] | None = None) -> tuple[dict[str, list[dict]], dict]:
    """({file name: records}, report); records get their split field set. fixed: seed_id -> split kept from
    the last run (splits.yaml)."""
    near = similar_pairs(in_domain)
    groups = seed_groups(in_domain, near)
    info = {r["seed_id"]: (r["case_type"], r["domain"]) for r in in_domain}
    fixed = {s: sp for s, sp in (fixed or {}).items() if s in info}
    where = assign(groups, info, fixed)
    for r in in_domain:
        r["split"] = where[r["seed_id"]]
    for r in ood:
        r["split"] = "test"
    files = {f"{sp}.jsonl": [r for r in in_domain if r["split"] == sp] for sp in SPLITS}
    files["ood_test.jsonl"] = list(ood)
    files = {k: sorted(v, key=lambda r: r["record_id"]) for k, v in files.items()}

    # what must hold by construction; checked again so a later change cannot break it silently
    policies = {sp: {p for r in files[f"{sp}.jsonl"] for p in r["gold"]["policy_ids"]} for sp in SPLITS}
    crossing_policies = sorted((policies["train"] & (policies["val"] | policies["test"])) | (policies["val"] & policies["test"]))
    seed_of = {r["record_id"]: r["seed_id"] for r in in_domain}
    crossing_near = [p for p in near if where[seed_of[p["a"]]] != where[seed_of[p["b"]]]]
    ood_twins = sorted({r["seed_id"] for r in ood if set(r["gold"]["policy_ids"]) & policies["train"]})
    report = {
        "method": "by seed, seeds sharing a gold policy or a near-duplicate kept together, greedy on case type "
                  "and domain counts", "ratios": RATIOS, "seed": SEED,
        "seeds_kept_from_splits_yaml": len(fixed), "seeds_newly_placed": len(info) - len(fixed),
        "groups": {"n": len(groups), "largest": max(len(g) for g in groups),
                   "multi_seed": [g for g in groups if len(g) > 1]},
        "near_duplicate_pairs": near, "policies_in_two_splits": crossing_policies,
        "near_duplicates_across_splits": crossing_near,
        "ood_seeds_sharing_a_policy_id_with_train": {"n": len(ood_twins), "seeds": ood_twins,
                                                     "note": "reworded OOD seeds reuse the in-domain rule and id by "
                                                             "design; the prompt hides ids and OOD uses the reworded text"},
        "splits": {name.removesuffix(".jsonl"): counts(rows) for name, rows in files.items()},
    }
    return files, report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--relock", action="store_true", help="allow the locked test files to change")
    ap.add_argument("--reassign", action="store_true", help="ignore splits.yaml and place every seed again")
    args = ap.parse_args(argv)
    set_seed(SEED)
    in_domain = list(read_jsonl(RECORDS / "all_in_domain.jsonl"))
    ood = list(read_jsonl(RECORDS / "all_ood.jsonl"))
    try:
        files, report = split(in_domain, ood, None if args.reassign else listed_splits())
    except SplitConflict as e:
        print(f"{e}: decide on purpose (move the seed in splits.yaml, or --reassign) and add a Changelog row",
              file=sys.stderr)
        return 1
    if report["policies_in_two_splits"] or report["near_duplicates_across_splits"]:
        print("a policy or a near duplicate crosses splits:", report["policies_in_two_splits"],
              report["near_duplicates_across_splits"], file=sys.stderr)
        return 1

    # write to a temporary name first, so a refused relock leaves every file as it was
    tmp = {name: RECORDS / f".{name}.new" for name in files}
    for name, rows in files.items():
        write_jsonl(tmp[name], rows)
    new_hashes = {f"data/records/{name}": sha256(tmp[name]) for name in LOCKED_FILES}
    old_hashes = read_lock()
    if old_hashes and old_hashes != new_hashes and not args.relock:
        for p in tmp.values():
            p.unlink()
        print(f"the locked test files would change ({LOCK}); rerun with --relock only on purpose", file=sys.stderr)
        return 1
    for name, p in tmp.items():
        p.replace(RECORDS / name)
    write_jsonl(RECORDS / "all_in_domain.jsonl", sorted(in_domain, key=lambda r: r["record_id"]))
    write_jsonl(RECORDS / "all_ood.jsonl", sorted(ood, key=lambda r: r["record_id"]))
    seeds = {sp: sorted({r["seed_id"] for r in files[f"{sp}.jsonl"]}) for sp in SPLITS}
    seeds["ood_test"] = sorted({r["seed_id"] for r in ood})
    (RECORDS / "splits.yaml").write_text(
        "# Seed ids per split. Written by python -m src.data_gen.split (decisions.md R11.3); do not edit by hand.\n"
        + yaml.safe_dump({"ratios": RATIOS, "seed": SEED, **seeds}, sort_keys=False), encoding="utf-8")
    LOCK.write_text(lock_text(new_hashes), encoding="utf-8")
    write_json(REPORTS / "split_report.json", report)
    for name, c in report["splits"].items():
        print(f"{name:9} {c['seeds']:3} seeds {c['records']:3} records  {c['case_type']}")
    print(f"groups {report['groups']['n']} (largest {report['groups']['largest']}), "
          f"near duplicates {len(report['near_duplicate_pairs'])}, seeds kept from splits.yaml "
          f"{report['seeds_kept_from_splits_yaml']}, newly placed {report['seeds_newly_placed']}, "
          f"lock {'unchanged' if old_hashes == new_hashes else 'written'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
