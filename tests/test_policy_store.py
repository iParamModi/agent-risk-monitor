"""The policy store (two text files) must stay consistent with the seeds (PLAN Step 5).

Checks the committed data/policies/*.jsonl against data/seeds/ via seed_extract, so a seed change
that was not re-generated (python scripts/gen_policy_store.py) fails CI.
"""
import yaml

from src.common.io import REPO_ROOT, read_jsonl
from src.policies.seed_extract import load_seeds
from src.policies.store import load_policies

POL = REPO_ROOT / "data" / "policies"
DECISIONS = {"ALLOW", "ASK_CONFIRMATION", "BLOCK", "ESCALATE"}
RISK_TYPES = {"DATA_LOSS", "PRIVACY_LEAKAGE", "FINANCIAL_LOSS", "ACCESS_CONTROL",
              "SECURITY", "OTHER", "NONE"}


def _logic():
    return yaml.safe_load((POL / "policy_logic.yaml").read_text(encoding="utf-8"))


def _conflict_pairs_from_seeds():
    pairs = set()
    for which in ("in_domain", "ood"):
        for d in load_seeds(which):
            if d["case_type"] == "T5" and d.get("t5_kind") == "policy_conflict" \
                    and len(d["gold_policy_ids"]) >= 2:
                pairs.add(tuple(sorted(d["gold_policy_ids"])))
    return pairs


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


# ---- policy_logic.yaml + conflicts.yaml --------------------------------------------------------

def test_logic_covers_every_store_policy():
    logic = set(_logic())
    assert set(_ids("policies.jsonl")) <= logic
    assert set(_ids("policies_ood.jsonl")) <= logic


def test_logic_fields_valid():
    for pid, e in _logic().items():
        assert e["decision"] in DECISIONS, pid
        assert e["risk_type"] in RISK_TYPES, pid
        assert e["fact_location"] in {"hidden_state", "in_policy"}, pid
        # ALLOW implies no harm; a firing decision implies a harm class
        assert (e["risk_type"] == "NONE") == (e["decision"] == "ALLOW"), pid


def test_conflicts_match_the_seeds_both_ways():
    stored = yaml.safe_load((POL / "conflicts.yaml").read_text(encoding="utf-8"))["conflicts"]
    stored_pairs = {tuple(sorted(c["policies"])) for c in stored}
    assert stored_pairs == _conflict_pairs_from_seeds()


def test_conflict_policies_exist_in_logic():
    logic = set(_logic())
    stored = yaml.safe_load((POL / "conflicts.yaml").read_text(encoding="utf-8"))["conflicts"]
    for c in stored:
        for pid in c["policies"]:
            assert pid in logic, f"{pid} in conflicts.yaml but not in policy_logic.yaml"
