"""The policy store (two text files) must stay consistent with the seeds (PLAN Step 5).

Checks the committed data/policies/*.jsonl against data/seeds/ via seed_extract, so a seed change
that was not re-generated (python scripts/gen_policy_store.py) fails CI.
"""
from src.common.io import REPO_ROOT, read_jsonl
from src.policies.seed_extract import load_seeds
from src.policies.store import load_policies

POL = REPO_ROOT / "data" / "policies"


def _ids(name):
    return [p["policy_id"] for p in read_jsonl(POL / name)]


def _seed_policy_ids(which):
    ids = set()
    for d in load_seeds(which):
        ids.update(d["gold_policy_ids"])
    return ids


def test_stores_load_without_error():
    # store.py raises on empty text or a duplicate id
    assert len(load_policies(POL / "policies.jsonl")) == 138
    assert len(load_policies(POL / "policies_ood.jsonl")) == 152


def test_no_duplicate_or_empty_text():
    for name in ("policies.jsonl", "policies_ood.jsonl"):
        pols = list(read_jsonl(POL / name))
        ids = [p["policy_id"] for p in pols]
        assert len(ids) == len(set(ids)), f"{name}: duplicate ids"
        assert all(p["text"].strip() for p in pols), f"{name}: empty text"


def test_every_seed_policy_is_in_its_store():
    assert _seed_policy_ids("in_domain") <= set(_ids("policies.jsonl"))
    assert _seed_policy_ids("ood") <= set(_ids("policies_ood.jsonl"))


def test_no_extra_ids_beyond_seeds():
    seeds_all = _seed_policy_ids("in_domain") | _seed_policy_ids("ood")
    assert set(_ids("policies.jsonl")) <= seeds_all
    assert set(_ids("policies_ood.jsonl")) <= seeds_all


def test_uniform_text_style():
    for name in ("policies.jsonl", "policies_ood.jsonl"):
        for p in read_jsonl(POL / name):
            t = p["text"]
            assert t[:1].isupper() and t[-1] in ".!?", f"{name}:{p['policy_id']}: {t!r}"


def test_reworded_ood_text_differs_from_in_domain():
    """A reworded OOD policy (seed note says 'reworded <PID>') must read differently from its twin,
    else the OOD generalization test is meaningless."""
    in_text = {p["policy_id"]: p["text"] for p in read_jsonl(POL / "policies.jsonl")}
    ood_text = {p["policy_id"]: p["text"] for p in read_jsonl(POL / "policies_ood.jsonl")}
    reworded = {pid for d in load_seeds("ood") for pid in d["gold_policy_ids"]
                if f"reworded {pid}" in d.get("notes", "")}
    assert reworded, "no reworded OOD policies detected"
    for pid in reworded:
        assert ood_text.get(pid) and ood_text[pid] != in_text.get(pid), f"{pid}: OOD text not reworded"
