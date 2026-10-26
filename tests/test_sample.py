"""src/external/sample.py on synthetic records."""
import random
from collections import Counter

import pytest

from src.external.sample import even_allocation, find_split, sample_train, split_stats


def make_records(n_groups=60, seed=0):
    """Groups of 1-12 records, mixed labels, 3 categories."""
    rng = random.Random(seed)
    records = []
    for g in range(n_groups):
        for i in range(rng.randint(1, 12)):
            records.append({"record_id": f"RJ-g{g}-{i}", "seed_id": f"RJ-scn-g{g}",
                            "gold": {"risk_label": rng.choice(["SAFE", "UNSAFE"])},
                            "meta": {"category": ["App", "Fin", "Web"][g % 3]}})
    return records


def test_groups_never_cross_splits_and_balance_holds():
    records = make_records()
    seed, where, stats = find_split(records, per_class=10)
    parts = {}
    for r in records:
        parts.setdefault(r["seed_id"], set()).add(where[r["seed_id"]])
    assert all(len(p) == 1 for p in parts.values())
    overall = sum(r["gold"]["risk_label"] == "UNSAFE" for r in records) / len(records)
    assert all(abs(st["unsafe_rate"] - overall) <= 0.05 for st in stats.values())
    assert sum(st["records"] for st in stats.values()) == len(records)


def test_split_is_repeatable():
    records = make_records()
    assert find_split(records, per_class=10) == find_split(records, per_class=10)


def test_sizes_near_70_10_20():
    records = make_records(n_groups=200)
    _, where, stats = find_split(records, per_class=10)
    n = len(records)
    assert abs(stats["test"]["records"] / n - 0.2) < 0.04
    assert abs(stats["val"]["records"] / n - 0.1) < 0.03


def test_sample_exact_per_class_and_spread():
    records = make_records(n_groups=120)
    seed, where, _ = find_split(records, per_class=30)
    train = [r for r in records if where[r["seed_id"]] == "train"]
    cat = lambda r: r["meta"]["category"]
    sample = sample_train(train, seed, cat, cat, per_class=30)
    labels = Counter(r["gold"]["risk_label"] for r in sample)
    assert labels == {"SAFE": 30, "UNSAFE": 30}
    assert len({r["record_id"] for r in sample}) == 60
    assert all(where[r["seed_id"]] == "train" for r in sample)
    per_cat = Counter(cat(r) for r in sample if r["gold"]["risk_label"] == "SAFE")
    assert max(per_cat.values()) - min(per_cat.values()) <= 1  # even when every category has enough


def test_even_allocation():
    assert even_allocation({"a": 100, "b": 100, "c": 100}, 150) == {"a": 50, "b": 50, "c": 50}
    assert even_allocation({"a": 5, "b": 100, "c": 100}, 150) == {"a": 5, "b": 73, "c": 72}  # small stratum capped
    with pytest.raises(ValueError):
        even_allocation({"a": 1}, 2)


def test_split_stats_counts():
    records = make_records(n_groups=10)
    where = {r["seed_id"]: "train" for r in records}
    st = split_stats(records, where)
    assert st["train"]["records"] == len(records) and st["test"]["records"] == 0


def test_replace_excluded_keeps_rest_and_swaps_same_label():
    from src.external.sample import replace_excluded
    records = make_records(n_groups=120)
    seed, where, _ = find_split(records, per_class=30)
    train = [r for r in records if where[r["seed_id"]] == "train"]
    cat = lambda r: r["meta"]["category"]
    sample = sample_train(train, seed, cat, cat, per_class=30)
    excluded = {sample[0]["record_id"], sample[-1]["record_id"]}
    new, swaps = replace_excluded(sample, train, excluded, cat, cat, seed)
    old_ids, new_ids = {r["record_id"] for r in sample}, {r["record_id"] for r in new}
    assert len(new) == len(sample) and not (new_ids & excluded)
    assert old_ids - excluded <= new_ids                      # everyone else stays
    by_id = {r["record_id"]: r for r in records}
    for out, inn in swaps:
        assert by_id[out]["gold"]["risk_label"] == by_id[inn]["gold"]["risk_label"]
        assert inn not in old_ids and where[by_id[inn]["seed_id"]] == "train"
    assert replace_excluded(sample, train, excluded, cat, cat, seed) == (new, swaps)  # repeatable


def test_load_excluded_ignores_comments(tmp_path):
    from src.external.sample import load_excluded
    f = tmp_path / "x.txt"
    f.write_text("# header\nRJ-a-1  # robot\n\nATB-2\n")
    assert load_excluded(f) == {"RJ-a-1", "ATB-2"}
    assert load_excluded(tmp_path / "missing.txt") == set()


def test_sample_skips_records_without_a_stratum():
    records = make_records()
    train = [r for r in records if r["meta"]["category"] != "Web" or r["gold"]["risk_label"] == "SAFE"] + \
        [r for r in records if r["meta"]["category"] == "Web" and r["gold"]["risk_label"] == "UNSAFE"]
    no_web = lambda r: None if r["meta"]["category"] == "Web" else r["meta"]["category"]   # noqa: E731
    sample = sample_train(train, 1, lambda r: "all", no_web, per_class=20)
    unsafe = [r for r in sample if r["gold"]["risk_label"] == "UNSAFE"]
    assert len(unsafe) == 20 and not any(r["meta"]["category"] == "Web" for r in unsafe)
    assert Counter(r["meta"]["category"] for r in unsafe) == {"App": 10, "Fin": 10}
