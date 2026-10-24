"""Splits our seeds (and, once they exist, our records) into tool phases.

Run: python scripts/split_by_phase.py [--seeds data/seeds] [--in data/records] [--out data/training]
                                      [--config configs/tool_phases.yaml]

Buckets, checked in this order (configs/tool_phases.yaml):
  rejected  a tool is in `dropped` or in no list at all
  ood       an OOD seed (id OOD-..., set "ood"), or a tool is in `ood_test_only`
  phase2    a tool is in `phase2` (anywhere, even an earlier read)
  phase1    every tool is in `phase1_in_domain`
A seed and all its records get ONE bucket: the worst one over every tool in every subtype,
so A/B pairs and T2 subtypes never land in different phases. Splits are kept as they are.
External records (R-Judge, ATBench) are not filtered; they are used in both phases.
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ORDER = ["rejected", "ood", "phase2", "phase1"]  # worst first
SPLITS = ["train", "val", "test"]


def load_phases(path: str | Path) -> dict[str, set[str]]:
    """Return {"phase1", "ood", "phase2", "dropped"} -> set of tool names; a tool may be in one list only."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    flat = lambda part: set(part.get("read", [])) | set(part.get("write", [])) if isinstance(part, dict) else set(part)
    phases = {"phase1": flat(raw["phase1_in_domain"]), "ood": flat(raw["ood_test_only"]),
              "phase2": flat(raw["phase2"]), "dropped": flat(raw["dropped"])}
    seen: Counter = Counter(t for tools in phases.values() for t in tools)
    twice = sorted(t for t, n in seen.items() if n > 1)
    if twice:
        raise ValueError(f"tools in more than one phase list: {twice}")
    return phases


def tools_in_record(record: dict) -> tuple[str, set[str]]:
    """(proposed action tool, every tool called in the trajectory) of one record."""
    action = record["visible"]["proposed_action"]["name"]
    traj = {m["tool_call"]["name"] for m in record["visible"]["trajectory"] if m.get("tool_call")}
    return action, traj


def tools_in_seed(seed: dict) -> tuple[str, set[str]]:
    """(proposed action tool, every read/write tool in the T2 subtypes) of one seed."""
    other = set()
    for sub in (seed.get("t2_subtypes") or {}).values():
        if not sub:
            continue
        if sub.get("earlier_read"):
            other.add(sub["earlier_read"]["tool"])
        if sub.get("later_write"):
            other.add(sub["later_write"]["name"])
    return seed["proposed_action"]["name"], other


def bucket_for_tools(tools: set[str], phases: dict[str, set[str]], is_ood: bool) -> tuple[str, list[str]]:
    """Return (bucket, the tools that decided it)."""
    known = phases["phase1"] | phases["ood"] | phases["phase2"]
    bad = sorted(t for t in tools if t in phases["dropped"] or t not in known)
    if bad:
        return "rejected", bad
    if is_ood or tools & phases["ood"]:
        return "ood", sorted(tools & phases["ood"])
    if tools & phases["phase2"]:
        return "phase2", sorted(tools & phases["phase2"])
    return "phase1", []


def bucket_for(record: dict, phases: dict[str, set[str]]) -> str:
    """Bucket of one record on its own (split_records then merges a seed's records)."""
    action, traj = tools_in_record(record)
    is_ood = record.get("set") == "ood" or record["seed_id"].startswith("OOD-")
    return bucket_for_tools({action} | traj, phases, is_ood)[0]


def bucket_for_seed(seed: dict, phases: dict[str, set[str]]) -> tuple[str, list[str]]:
    """Bucket of one seed over all its subtypes."""
    action, other = tools_in_seed(seed)
    return bucket_for_tools({action} | other, phases, seed["seed_id"].startswith("OOD-"))


def split_records(records: list[dict], phases: dict[str, set[str]]) -> dict[str, list[dict]]:
    """bucket -> records; every record of a seed goes to the worst bucket among them."""
    ours = [r for r in records if r.get("source", "ours") == "ours"]
    seed_bucket: dict[str, str] = {}
    for r in ours:
        b = bucket_for(r, phases)
        old = seed_bucket.get(r["seed_id"], "phase1")
        seed_bucket[r["seed_id"]] = min(b, old, key=ORDER.index)
    out: dict[str, list[dict]] = {b: [] for b in ORDER}
    for r in sorted(ours, key=lambda r: r["record_id"]):
        out[seed_bucket[r["seed_id"]]].append(r)
    return out


def split_seeds(seeds: list[dict], phases: dict[str, set[str]]) -> dict:
    """Seed ids per bucket, plus counts and reasons."""
    buckets: dict[str, list[str]] = {b: [] for b in ORDER}
    reasons: dict[str, list[str]] = {}
    actions: dict[str, Counter] = defaultdict(Counter)
    for seed in sorted(seeds, key=lambda s: s["seed_id"]):
        b, why = bucket_for_seed(seed, phases)
        buckets[b].append(seed["seed_id"])
        actions[b][seed["proposed_action"]["name"]] += 1
        if why and b != "ood":
            reasons[seed["seed_id"]] = why
    return {"counts": {b: len(ids) for b, ids in buckets.items()},
            "action_counts": {b: dict(sorted(c.items())) for b, c in actions.items()},
            "reasons": reasons, "seeds": buckets}


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


def write_record_files(buckets: dict[str, list[dict]], out: Path) -> dict:
    """Write phase{1,2}_{split}.jsonl, ood_test.jsonl, rejected.jsonl; return the summary."""
    warnings = []
    for phase in ("phase1", "phase2"):
        for split in SPLITS:
            _write_jsonl(out / f"{phase}_{split}.jsonl", [r for r in buckets[phase] if r["split"] == split])
    _write_jsonl(out / "ood_test.jsonl", buckets["ood"])
    _write_jsonl(out / "rejected.jsonl", buckets["rejected"])
    for r in buckets["ood"]:
        if r["split"] in ("train", "val"):
            warnings.append(f"OOD record {r['record_id']} is marked {r['split']}")
    no_split = [r["record_id"] for b in ("phase1", "phase2") for r in buckets[b] if r["split"] not in SPLITS]
    if no_split:
        warnings.append(f"{len(no_split)} records have no split yet and were not written: {no_split[:5]}")
    return {
        "counts": {b: dict(Counter(r["split"] for r in rows)) for b, rows in buckets.items()},
        "action_counts": {b: dict(sorted(Counter(r["visible"]["proposed_action"]["name"] for r in rows).items()))
                          for b, rows in buckets.items()},
        "rejected": {r["record_id"]: sorted({t for t in [tools_in_record(r)[0], *tools_in_record(r)[1]]})
                     for r in buckets["rejected"]},
        "warnings": warnings,
    }


def load_seeds(folder: Path) -> list[dict]:
    return [yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*/*.yaml"))]


def load_records(folder: Path) -> list[dict]:
    rows = []
    for p in sorted(folder.glob("**/*.jsonl")):
        rows += [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    for p in sorted(folder.glob("**/*.json")):
        rows.append(json.loads(p.read_text(encoding="utf-8")))
    return rows


def print_summary(title: str, counts: dict, action_counts: dict) -> None:
    print(f"\n{title}")
    for b in ORDER:
        print(f"  {b:9} {counts.get(b, 0)}")
    for b in ORDER:
        if action_counts.get(b):
            print(f"  {b} actions: {action_counts[b]}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds", default=ROOT / "data" / "seeds", type=Path)
    ap.add_argument("--in", dest="records", default=ROOT / "data" / "records", type=Path)
    ap.add_argument("--out", default=ROOT / "data" / "training", type=Path)
    ap.add_argument("--config", default=ROOT / "configs" / "tool_phases.yaml", type=Path)
    args = ap.parse_args(argv)
    phases = load_phases(args.config)
    args.out.mkdir(parents=True, exist_ok=True)

    seed_summary = split_seeds(load_seeds(args.seeds), phases)
    (args.out / "seed_phases.json").write_text(json.dumps(seed_summary, indent=2) + "\n", encoding="utf-8")
    print_summary("Seeds per bucket", seed_summary["counts"], seed_summary["action_counts"])
    for sid, why in seed_summary["reasons"].items():
        if sid in seed_summary["seeds"]["rejected"]:
            print(f"  rejected {sid}: {why}")

    records = load_records(args.records)
    if not records:
        print(f"\nNo records in {args.records} yet; only seed_phases.json was written.")
        return 0
    summary = write_record_files(split_records(records, phases), args.out)
    (args.out / "split_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print_summary("Records per bucket", {b: sum(c.values()) for b, c in summary["counts"].items()},
                  summary["action_counts"])
    for b, c in summary["counts"].items():
        print(f"  {b} by split: {c}")
    for w in summary["warnings"]:
        print(f"  WARNING: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
