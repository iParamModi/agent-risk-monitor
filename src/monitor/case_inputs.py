"""What run_monitor needs for one of our records (task decide_action), built the same way for every setting,
the evaluation runs and the interactive check (scripts/chat_monitor.py):

- policies, 3 shown, in one of two conditions (decisions.md 2026-10-28):
  "retrieval"  the top 3 retrieved for the tuned query (action + all user and agent turns, EVAL_W) from the
               in-domain store, or the OOD store for OOD records: the full system (PLAN 6)
  "gold"       the gold policies plus the best retrieved others up to 3, exactly as in the Phase B training file:
               checking and deciding measured as if retrieval were perfect. This condition reads gold.policy_ids
               to choose what is shown; the prompt still shows numbers only, and a T1/T2 decision still needs a check
- check_tools: the check tools the prompt lists (OOD-only tools on OOD records only), R7.1
- gateway: src/gateway one per record and setting (selective is capped at 4 calls), R7.3-R7.6
- table_checks: the always setting's checks for the proposed action, filled from configs/check_table.yaml, R7.5

Apart from the "gold" policy condition nothing here reads gold. The embedding model is loaded once and shared.

System versions (decisions.md 2026-11-11; VERSIONS): "v1" is the system of the 30 Oct and 11 Nov final runs. "v2"
changes inference only (no retraining): retrieval ranks only the policies tagged with the proposed action's tool
(data/policies/policy_tags.yaml) and shows 8 instead of 3; selective adds the second-source check
(loop.second_source_calls) and the two prompt hints. The "gold" condition keeps gold + 2 look-alikes in every
version, as in training.
"""
from src.common.io import REPO_ROOT
from src.monitor.check_tools import load_check_tools
from src.policies.retriever import EVAL_W, Retriever, query_for
from src.policies.store import IN_DOMAIN, OOD, load_policies, load_policy_tags

POLICY_MODES = ("retrieval", "gold")
N_SHOWN = 3
FACT_CHECKS = REPO_ROOT / "configs" / "fact_checks.yaml"
VERSIONS = {
    "v1": {"tags": False, "shown": N_SHOWN, "second_source": False, "hints": False},
    "v2": {"tags": True, "shown": 8, "second_source": True, "hints": True},
    "v2_retrieval": {"tags": True, "shown": 8, "second_source": False, "hints": False},   # val check only
}


def sibling_map(include_ood: bool, path=FACT_CHECKS) -> dict:
    """attribute -> [(tool, resource param)] for every fact that two or more check tools report
    (configs/fact_checks.yaml); OOD-only tools only for OOD records."""
    import yaml
    out = {}
    for fact, tools in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).items():
        tools = [(t["tool"], t["resource_param"]) for t in tools if include_ood or not t.get("ood")]
        if len({tool for tool, _ in tools}) >= 2:
            out[fact] = tools
    return out


class CaseInputs:
    def __init__(self, embedder=None, w: float = EVAL_W, policy_mode: str = "retrieval", version: str = "v1"):
        if policy_mode not in POLICY_MODES:
            raise ValueError(f"policy_mode must be one of {POLICY_MODES}")
        if version not in VERSIONS:
            raise ValueError(f"version must be one of {tuple(VERSIONS)}")
        self.embedder, self.w, self.policy_mode, self.version = embedder, w, policy_mode, version
        self.config = VERSIONS[version]
        self._retrievers: dict[str, Retriever] = {}
        self._tools: dict[bool, list[dict]] = {}
        self._siblings: dict[bool, dict] = {}

    def retriever(self, set_name: str) -> Retriever:
        if set_name not in self._retrievers:
            if self.embedder is None:
                from src.policies.retriever import BgeEmbedder
                self.embedder = BgeEmbedder()
            store = OOD if set_name == "ood" else IN_DOMAIN
            tags = load_policy_tags() if self.config["tags"] else None
            self._retrievers[set_name] = Retriever(load_policies(store), embedder=self.embedder, w=self.w, tags=tags)
        return self._retrievers[set_name]

    def policies(self, record: dict) -> list[dict]:
        retriever = self.retriever(record["set"])
        query = query_for(record["visible"], all_turns=True)
        if self.policy_mode == "retrieval":
            tool = record["visible"]["proposed_action"]["name"] if self.config["tags"] else None
            return retriever.search(query, k=self.config["shown"], tool=tool)
        gold_ids = record["gold"]["policy_ids"]
        by_id = {p["policy_id"]: p for p in retriever.policies}
        need = max(0, N_SHOWN - len(gold_ids))
        others = [p for p in retriever.search(query, k=need + len(gold_ids), tool=None)
                  if p["policy_id"] not in gold_ids][:need]
        return [{"policy_id": p["policy_id"], "text": p["text"]} for p in [by_id[g] for g in gold_ids] + others]

    def for_record(self, record: dict, setting: str, run_id: str = "") -> dict:
        """Keyword arguments for run_monitor (besides record, setting and model)."""
        from src.gateway.gateway import _requested_by, for_record, table_calls
        ood = record["set"] == "ood"
        if ood not in self._tools:
            self._tools[ood] = load_check_tools(include_ood=ood)
        action = record["visible"]["proposed_action"]
        current_user = _requested_by(record["seed_id"], record["set"])    # the acting user, never gold
        if ood not in self._siblings:
            self._siblings[ood] = sibling_map(include_ood=ood)
        v2 = {"siblings": self._siblings[ood] if self.config["second_source"] else None, "hints": self.config["hints"]}
        return {**v2, "policies": self.policies(record), "check_tools": self._tools[ood],
                "gateway": for_record(record, setting=setting, run_id=run_id),
                "table_checks": [{"tool": t, "args": a} for t, a in table_calls(action, current_user)]}
