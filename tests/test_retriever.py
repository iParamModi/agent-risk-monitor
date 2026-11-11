"""Policy store, temporary policy builder, retriever scoring and the retrieval report.

A tiny word-count embedder stands in for bge here so the tests run in milliseconds; real runs use bge.
"""
import importlib.util
import math
import re

import pytest

from src.common.io import write_jsonl
from src.policies import retriever as r
from src.policies.store import load_policies

POLICIES = [
    {"policy_id": "P_FIN_01", "text": "Transfers above the user's approval limit need human approval."},
    {"policy_id": "P_FIN_09", "text": "No payments may be sent to accounts on the sanctions list."},
    {"policy_id": "P_FILE_01", "text": "Files classified 'restricted' must never be deleted."},
    {"policy_id": "P_CAL_01", "text": "Meeting invites with attachments must not go to external guests."},
]


class WordEmbedder:
    """Bag-of-words vectors over a fixed vocabulary, L2-normalized (test stand-in for bge)."""

    def __init__(self, texts):
        self.vocab = sorted({w for t in texts for w in r.tokenize(t)})

    def encode(self, texts, is_query=False):
        out = []
        for t in texts:
            words = r.tokenize(t)
            v = [float(words.count(w)) for w in self.vocab]
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out


def make_retriever(w=0.5):
    return r.Retriever(POLICIES, embedder=WordEmbedder([p["text"] for p in POLICIES]), w=w)


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, f"scripts/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------- text handling ----------

def test_tokenize_splits_ids_and_drops_plurals_and_stopwords():
    assert r.tokenize("transfer_money to acct_77: Transfers of the FILES") == \
        ["transfer", "money", "acct", "77", "transfer", "file"]
    assert r.tokenize("access") == ["access"]       # 'ss' is kept


def test_build_query_uses_action_and_request():
    action = {"name": "transfer_money", "args": {"to_account": "acct_77", "amount_inr": 350000}}
    assert r.build_query(action, " Pay the vendor. ") == \
        "transfer money. to account: acct_77; amount inr: 350000. Pay the vendor."
    assert r.build_query({"name": "delete_file", "args": {}}) == "delete file"


def test_min_max_and_combine():
    assert r.min_max([2.0, 4.0, 6.0]) == [0.0, 0.5, 1.0]
    assert r.min_max([3.0, 3.0]) == [0.0, 0.0]
    assert r.combine([0.0, 10.0], [1.0, 0.0], w=0.0) == [0.0, 1.0]    # BM25 only
    assert r.combine([0.0, 10.0], [1.0, 0.0], w=1.0) == [1.0, 0.0]    # embeddings only
    assert r.combine([0.0, 10.0], [1.0, 0.0], w=0.25) == [0.25, 0.75]


def test_top_indices_is_stable_on_ties():
    assert r.top_indices([0.5, 0.9, 0.5, 0.1], 3) == [1, 0, 2]


# ---------- retriever ----------

def test_search_returns_the_loop_format():
    hits = make_retriever().search("payment to an account on the sanctions list", k=2)
    assert hits[0] == {"policy_id": "P_FIN_09", "text": POLICIES[1]["text"]}
    assert len(hits) == 2 and set(hits[0]) == {"policy_id", "text"}


def test_for_action_finds_the_matching_policy():
    hits = make_retriever().for_action({"name": "delete_file", "args": {"file": "plan.pdf"}},
                                       "Delete the restricted file")
    assert hits[0]["policy_id"] == "P_FILE_01"


def test_w_picks_between_keyword_and_meaning_scores():
    ret = make_retriever()
    keyword, meaning = ret.raw_scores("approval limit")
    assert len(keyword) == len(meaning) == len(POLICIES)
    assert ret.rank("approval limit", k=1, w=0.0) == ret.rank("approval limit", k=1, w=1.0) == [0]


def test_retriever_reads_only_visible_text():
    hidden = [{**POLICIES[0], "actions": "transfer_money", "decision": "ASK_CONFIRMATION"}]
    ret = r.Retriever(hidden, embedder=WordEmbedder([hidden[0]["text"]]))
    assert ret.search("ASK_CONFIRMATION transfer_money", k=1)[0] == {"policy_id": "P_FIN_01", "text": POLICIES[0]["text"]}
    keyword, _ = ret.raw_scores("ASK_CONFIRMATION")
    assert keyword == [0.0]      # hidden fields are not indexed


# ---------- store ----------

def test_load_policies_checks_fields_and_duplicates(tmp_path):
    good = tmp_path / "p.jsonl"
    write_jsonl(good, POLICIES)
    assert load_policies(good) == POLICIES
    write_jsonl(tmp_path / "dup.jsonl", POLICIES + [POLICIES[0]])
    with pytest.raises(ValueError):
        load_policies(tmp_path / "dup.jsonl")
    write_jsonl(tmp_path / "empty.jsonl", [{"policy_id": "P_X_01", "text": ""}])
    with pytest.raises(ValueError):
        load_policies(tmp_path / "empty.jsonl")


# ---------- temporary policy builder ----------

IN_MD = """| Policy | Text | Case | Action(s) | Fact | Decision | #seeds |
|---|---|---|---|---|---|---|
| `P_FIN_01` | Transfers above the user's approval limit need human approval. | T1 | transfer_money | `approval_limit_inr` | ASK_CONFIRMATION | 1 |
| `P_FIN_05` | invoices must be paid on or before the due date | T5 | transfer_money | - | ESCALATE | 1 |
"""
OOD_MD = """| `P_CUST_01` | Customer data may be exported only with consent. | T1 | export_customer_data | `consent` | BLOCK | 4 |
| `P_FIN_01` | FIN | Payments over a person's sign-off limit need a human to approve them. | Transfers above ... | `approval_limit_inr` |
"""


def test_build_policies_keeps_only_visible_text():
    bp = load_script("build_policies")
    base = bp.in_domain(IN_MD)
    assert base == [{"policy_id": "P_FIN_01", "text": "Transfers above the user's approval limit need human approval."},
                    {"policy_id": "P_FIN_05", "text": "invoices must be paid on or before the due date"}]
    assert bp.style_notes(base) == ["P_FIN_05"]


def test_build_ood_replaces_reworded_and_adds_new_domain():
    bp = load_script("build_policies")
    store = bp.ood(OOD_MD, bp.in_domain(IN_MD))
    assert [p["policy_id"] for p in store] == ["P_FIN_01", "P_FIN_05", "P_CUST_01"]
    assert store[0]["text"].startswith("Payments over a person's sign-off limit")
    with pytest.raises(ValueError):
        bp.ood("| `P_ZZZ_09` | FIN | new words | old words | - |\n", bp.in_domain(IN_MD))


# ---------- report ----------

def test_score_ranking_by_hand():
    ev = load_script("eval_retrieval")
    golds = [["A"], ["B"], ["C", "D"], ["E", "F"]]
    ranked = [["A", "x", "y", "z", "q"], ["x", "y", "z", "B", "q"], ["C", "D", "x", "y", "z"], ["E", "x", "y", "F", "z"]]
    s = ev.score_ranking(golds, ranked, ["T1", "T1", "T5", "T5"])
    assert s["recall@1"] == 0.75 and s["recall@3"] == 0.75 and s["recall@5"] == 1.0
    assert s["full_recall@3"] == 0.5          # A, and C+D; E+F only half
    assert s["conflict_recall@3"] == 0.5 and s["conflict_seeds"] == 2


def test_choose_w_prefers_best_then_closest_to_half():
    ev = load_script("eval_retrieval")
    assert ev.choose_w({0.2: {"recall@3": 0.8}, 0.6: {"recall@3": 0.8}, 0.9: {"recall@3": 0.7}}) == 0.6
    assert ev.choose_w({0.0: {"recall@3": 0.9}, 0.5: {"recall@3": 0.8}}) == 0.0


def test_evaluate_runs_on_tiny_seeds():
    ev = load_script("eval_retrieval")
    seeds = [{"seed_id": "S1", "domain": "FIN", "case_type": "T4", "gold_policy_ids": ["P_FIN_09"],
              "proposed_action": {"name": "transfer_money", "args": {}}, "story_hint": "Pay a sanctions list account."},
             {"seed_id": "S2", "domain": "FILE", "case_type": "T1", "gold_policy_ids": ["P_FILE_01"],
              "proposed_action": {"name": "delete_file", "args": {}}, "story_hint": "Delete a restricted file."}]
    rep = ev.evaluate(seeds, make_retriever())
    assert set(rep["by_w"]) == {str(w) for w in ev.W_VALUES}
    assert rep["at_chosen_w"]["overall"]["recall@3"] == 1.0 and rep["at_chosen_w"]["misses"] == []
    assert re.search(r"\| 0\.\d", ev.to_markdown({"policies": 4, "seeds": 2, **rep}))


def test_tags_rank_only_the_tools_policies_and_fall_back_without_tags():
    tags = {"P_FIN_01": {"transfer_money"}, "P_FIN_09": {"transfer_money"}, "P_FILE_01": {"delete_file"}}
    ret = r.Retriever(POLICIES, embedder=WordEmbedder([p["text"] for p in POLICIES]), w=0.5, tags=tags)
    shown = [p["policy_id"] for p in ret.search("delete the restricted file", k=3, tool="transfer_money")]
    assert sorted(shown) == ["P_FIN_01", "P_FIN_09"]                     # k is cut to the tagged policies
    assert [p["policy_id"] for p in ret.search("delete the file", k=1, tool="delete_file")] == ["P_FILE_01"]
    assert len(ret.search("anything", k=3, tool="create_event")) == 3    # no policy tagged: whole store
    assert len(ret.search("anything", k=3)) == 3                         # no tool: whole store


def test_policy_tags_file_is_up_to_date_and_covers_every_gold_policy():
    from src.common.io import REPO_ROOT, read_jsonl
    from src.policies.store import load_policy_tags
    spec = importlib.util.spec_from_file_location("gen_policy_tags", REPO_ROOT / "scripts" / "gen_policy_tags.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    assert gen.OUT.read_text(encoding="utf-8") == gen.build(), "run python scripts/gen_policy_tags.py"
    tags = load_policy_tags()
    for p in load_policies() + load_policies(REPO_ROOT / "data" / "policies" / "policies_ood.jsonl"):
        assert tags.get(p["policy_id"]), p["policy_id"]
    for split in ("train", "val"):
        for rec in read_jsonl(REPO_ROOT / "data" / "records" / f"{split}.jsonl"):
            for pid in rec["gold"]["policy_ids"]:
                assert rec["visible"]["proposed_action"]["name"] in tags[pid], (rec["record_id"], pid)
