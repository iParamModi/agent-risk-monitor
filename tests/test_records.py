"""The committed records in data/records/ (Step 9 merge + Step 11 split) still pass every check.

Guards the frozen data: a hand edit that breaks a label rule, a leak, a T1 pair or the split shows up here.
"""
from collections import defaultdict

import pytest
import yaml

from src.common.io import REPO_ROOT, read_jsonl
from src.data_gen.auto_checks import check_dataset, check_record
from src.data_gen.leakage_check import check_pairs
from src.data_gen.merge import RECORD_KEYS, load_check_specs, load_seeds, read_tool_names
from src.policies.store import IN_DOMAIN, OOD, load_policies

RECORDS = REPO_ROOT / "data" / "records"


@pytest.fixture(scope="module")
def data():
    files = {name: list(read_jsonl(RECORDS / f"{name}.jsonl"))
             for name in ("all_in_domain", "all_ood", "train", "val", "test", "ood_test")}
    return files, load_seeds()


def test_every_record_passes_the_merge_checks(data):
    files, seeds = data
    records = files["all_in_domain"] + files["all_ood"]
    stores = {"in_domain": {p["policy_id"] for p in load_policies(IN_DOMAIN)},
              "ood": {p["policy_id"] for p in load_policies(OOD)}}
    reads, specs = read_tool_names(), load_check_specs()
    problems = [p for r in records for p in check_record(r, seeds[r["seed_id"]], stores[r["set"]], reads, specs)[0]]
    problems += check_dataset(records, seeds)
    problems += [f["seed_id"] for f in check_pairs(records)["failed"]]
    assert problems == []
    assert all(list(r) == list(RECORD_KEYS) for r in records)
    assert all(isinstance(r["meta"]["n_tokens"], int) for r in records)


def test_split_files_are_the_split_of_the_merged_files(data):
    files, _ = data
    by_split = defaultdict(list)
    for r in files["all_in_domain"]:
        by_split[r["split"]].append(r)
    assert set(by_split) == {"train", "val", "test"}
    for split in ("train", "val", "test"):
        assert files[split] == by_split[split]
    assert files["ood_test"] == files["all_ood"] and {r["split"] for r in files["all_ood"]} == {"test"}
    assert {r["set"] for r in files["all_ood"]} == {"ood"} and {r["set"] for r in files["all_in_domain"]} == {"in_domain"}


def test_seeds_and_policies_never_cross_splits(data):
    files, _ = data
    split_of, policy_splits = {}, defaultdict(set)
    for r in files["all_in_domain"]:
        assert split_of.setdefault(r["seed_id"], r["split"]) == r["split"], r["record_id"]
        for pid in r["gold"]["policy_ids"]:
            policy_splits[pid].add(r["split"])
    assert {pid: s for pid, s in policy_splits.items() if len(s) > 1} == {}
    listed = yaml.safe_load((RECORDS / "splits.yaml").read_text(encoding="utf-8"))
    for split in ("train", "val", "test"):
        assert listed[split] == sorted(s for s, sp in split_of.items() if sp == split)
    assert listed["ood_test"] == sorted({r["seed_id"] for r in files["all_ood"]})
