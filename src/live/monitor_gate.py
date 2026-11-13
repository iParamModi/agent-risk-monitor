"""The real monitor as an lma_agent gate: every proposed write goes through run_monitor before it runs.

    gate = MonitorGate(model, setting="selective")            # version "v2": the final system
    run_agent(task, state, client, gate=gate, on_event=sink)

For each write: the visible record (src.live.live_record), the retrieved policies (the evaluation query: action +
every user and agent turn, EVAL_W), a gateway over the LIVE company state (src.gateway.gateway.for_state, noise
off), then run_monitor. The decision comes only from run_monitor; check results only from the gateway.

Every system setting comes from ONE place, src.monitor.case_inputs.VERSIONS[version], the same entry the evaluation
runs use (CaseInputs), so live and eval cannot drift apart: k = "shown" (v2: 8), the tool-tag filter ("tags"), the
second-source check ("second_source"), the prompt hints ("hints"), and "action_tools" / "second_ask" when a version
has them. There is no separate k argument on purpose. Default "v2" = the final system (decisions.md 2026-11-11/12).
An invalid monitor answer is treated as ESCALATE (a human decides), never as ALLOW.
"""
import time

from lma_agent.sim.models import CompanyState, GateDecision, Task, ToolCall
from src.gateway.gateway import for_state, table_calls
from src.live.live_record import record_from_live
from src.monitor.case_inputs import VERSIONS, sibling_map
from src.monitor.check_tools import load_check_tools
from src.monitor.loop import run_monitor
from src.monitor.parser import parse_output
from src.monitor.prompt_builder import number_policies
from src.policies.retriever import EVAL_W, Retriever, query_for
from src.policies.store import IN_DOMAIN, load_policies, load_policy_tags


class KeywordOnlyEmbedder:
    """No meaning part: every vector is the same, so the retriever ranks by BM25 alone. For CPU runs without
    sentence-transformers (FakeModel demos, tests); real runs use BgeEmbedder."""

    def encode(self, texts, is_query=False):
        return [[1.0] for _ in texts]


def first_line(text: str) -> str:
    return text.strip().splitlines()[0] if text.strip() else ""


class _EmittingModel:
    """Wraps the monitor model: one monitor_pass event per pass (pass 1 = before any check, later = after)."""

    def __init__(self, model, emit, gateway):
        self.inner, self.emit, self.gateway, self.name, self.n = model, emit, gateway, model.name, 0

    def generate(self, messages):
        t0 = time.perf_counter()
        gen = self.inner.generate(messages)
        latency = round(time.perf_counter() - t0, 3)
        self.n += 1
        obj = parse_output(gen.text, ("DECISION", "NEED_INFORMATION"))
        payload = {"pass": self.n, "type": obj["type"] if obj else "INVALID", "output": obj,
                   "tokens_in": gen.tokens_in, "tokens_out": gen.tokens_out, "latency_s": latency}
        if obj is None:
            payload["raw"] = (gen.text or "")[:2000]
        self.emit("monitor_pass1" if self.n == 1 and not self.gateway.calls else "monitor_pass2", payload)
        return gen


class _EmittingGateway:
    """Wraps the gateway: one gateway_check event per call, with the result the monitor saw."""

    def __init__(self, gateway, emit):
        self.inner, self.emit, self.calls = gateway, emit, []

    def call(self, tool, args):
        result = self.inner.call(tool, args)
        self.calls.append({"tool": tool, "args": args, "result": result})
        self.emit("gateway_check", {"index": len(self.calls), "tool": tool, "args": args, "result": result})
        return result


class MonitorGate:
    def __init__(self, model, setting: str = "selective", version: str = "v2", embedder=None,
                 retriever: Retriever | None = None, task: Task | None = None, run_id: str = "live"):
        if version not in VERSIONS:
            raise ValueError(f"version must be one of {tuple(VERSIONS)}")
        self.model, self.setting, self.task, self.run_id = model, setting, task, run_id
        self.version = version
        self.config = dict(VERSIONS[version])           # the one source of every system setting
        self.k = self.config["shown"]
        if retriever is None:
            tags = load_policy_tags() if self.config["tags"] else None
            retriever = Retriever(load_policies(IN_DOMAIN), embedder=embedder, w=EVAL_W, tags=tags)
        self.retriever = retriever
        self.check_tools = load_check_tools(include_ood=False)
        self.siblings = sibling_map(include_ood=False) if self.config["second_source"] else None
        self.state: CompanyState | None = None
        self.emit = lambda type, payload: None
        self.step = 0
        self.rows: list[dict] = []       # run_monitor rows, one per judged write

    @property
    def settings(self) -> dict:
        """What this gate runs, for the run log: the version name, k and the VERSIONS entry it was read from."""
        return {"monitor_version": self.version, "k": self.k, **self.config}

    def observe(self, state: CompanyState, emit, step: int) -> None:
        """Called by the agent loop before each write: the live state, the event callback, the step."""
        self.state, self.emit, self.step = state, emit, step

    def __call__(self, messages: list[dict], call: ToolCall) -> GateDecision:
        if self.state is None:
            raise RuntimeError("MonitorGate needs the live state: run it through lma_agent's run_agent")
        task = self.task or Task(task_id="live", domain="LIVE", prompt="")
        record = record_from_live(task, messages, call, record_id=f"{self.run_id}-s{self.step}-{call.id}")
        action = record["visible"]["proposed_action"]

        tool = action["name"] if self.config["tags"] else None
        policies = self.retriever.search(query_for(record["visible"], all_turns=True), k=self.k, tool=tool)
        numbered = {p["policy_id"]: p["ref"] for p in number_policies(policies, record["record_id"])}
        self.emit("policies", {"policies": [{"policy_id": p["policy_id"], "ref": numbered[p["policy_id"]],
                                             "first_line": first_line(p["text"]), "text": p["text"]}
                                            for p in policies]})

        table = [{"tool": t, "args": a} for t, a in table_calls(action, self.state.current_user)]
        check_tools = self.check_tools
        if self.config.get("action_tools"):          # as CaseInputs.for_record: only this action's table tools
            names = {c["tool"] for c in table}
            check_tools = [t for t in check_tools if t["name"] in names] or check_tools
        gateway = _EmittingGateway(for_state(self.state, self.setting, run_id=self.run_id,
                                             case_id=record["record_id"], action=action), self.emit)
        model = _EmittingModel(self.model, self.emit, gateway)
        row = run_monitor(record, self.setting, model, gateway=gateway, policies=policies,
                          check_tools=check_tools, table_checks=table, siblings=self.siblings,
                          hints=self.config["hints"], second_ask=bool(self.config.get("second_ask")))
        self.rows.append(row)
        return self._decide(row, len(table))

    def _decide(self, row: dict, checks_always: int) -> GateDecision:
        out = row["output"]
        valid = bool(out) and out.get("type") == "DECISION"
        ids = list(out["evidence"]["policy_ids"]) if valid else []
        facts = list(out["evidence"]["facts"]) if valid else []
        decision = out["decision"] if valid else "ESCALATE"
        self.emit("decision", {"decision": decision, "valid": valid,
                               "risk_label": out.get("risk_label") if valid else None,
                               "risk_type": out.get("risk_type") if valid else None,
                               "evidence": facts, "policy_ids": ids,
                               "checks_used": len(row["calls"]), "checks_always": checks_always,
                               "passes": row["passes"], "setting": self.setting, "model": self.model.name,
                               "monitor_version": self.version, "k": self.k})
        reason = "; ".join(facts) if valid else "the monitor gave no valid decision, a human must decide"
        return GateDecision(decision=decision, policy_id=ids[0] if ids else None, reason=reason[:300])
