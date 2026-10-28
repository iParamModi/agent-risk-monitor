"""What run_monitor needs for one of our records (task decide_action), built the same way for every setting,
the evaluation runs and the interactive check (scripts/chat_monitor.py):

- policies: top 3 retrieved for the record's query (in-domain store, or the OOD store for OOD records), PLAN 6
- check_tools: the check tools the prompt lists (OOD-only tools on OOD records only), R7.1
- gateway: src/gateway one per record and setting (selective is capped at 4 calls), R7.3-R7.6
- table_checks: the always setting's checks for the proposed action, filled from configs/check_table.yaml, R7.5

Nothing here reads gold. The retriever's embedding model is loaded once and shared by both stores.
"""
from src.monitor.check_tools import load_check_tools
from src.policies.retriever import DEFAULT_W, Retriever, query_for
from src.policies.store import IN_DOMAIN, OOD, load_policies


class CaseInputs:
    def __init__(self, embedder=None, w: float = DEFAULT_W):
        self.embedder, self.w = embedder, w
        self._retrievers: dict[str, Retriever] = {}

    def retriever(self, set_name: str) -> Retriever:
        if set_name not in self._retrievers:
            if self.embedder is None:
                from src.policies.retriever import BgeEmbedder
                self.embedder = BgeEmbedder()
            store = OOD if set_name == "ood" else IN_DOMAIN
            self._retrievers[set_name] = Retriever(load_policies(store), embedder=self.embedder, w=self.w)
        return self._retrievers[set_name]

    def for_record(self, record: dict, setting: str, run_id: str = "") -> dict:
        """Keyword arguments for run_monitor (besides record, setting and model)."""
        from src.gateway.gateway import _requested_by, for_record, table_calls
        action = record["visible"]["proposed_action"]
        current_user = _requested_by(record["seed_id"], record["set"])    # the acting user, never gold
        return {"policies": self.retriever(record["set"]).search(query_for(record["visible"])),
                "check_tools": load_check_tools(include_ood=record["set"] == "ood"),
                "gateway": for_record(record, setting=setting, run_id=run_id),
                "table_checks": [{"tool": t, "args": a} for t, a in table_calls(action, current_user)]}
