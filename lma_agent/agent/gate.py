"""Gates decide what happens to a write: allow_all, fake_gate (tests) and monitor_gate (the real monitor)."""
from collections.abc import Callable

from lma_agent.sim.models import GateDecision, ToolCall

Gate = Callable[[list[dict], ToolCall], GateDecision]


def allow_all(messages: list[dict], call: ToolCall) -> GateDecision:
    """Allow every write."""
    return GateDecision(decision="ALLOW")


def fake_gate(fixed: str, policy_id: str | None = "P_TEST", reason: str = "fake gate") -> Gate:
    """Return a gate that always gives the decision `fixed` (for testing the 4 branches)."""
    def gate(messages: list[dict], call: ToolCall) -> GateDecision:
        return GateDecision(decision=fixed, policy_id=policy_id, reason=reason)
    return gate


def monitor_gate(model, setting: str = "selective", **kwargs) -> Gate:
    """The real monitor (src.monitor.loop.run_monitor) as a gate, over the LIVE company state.

    model: has generate(messages) (src/monitor/models.py, or src.live.fake_monitor.RuleFakeMonitor on CPU).
    kwargs go to src.live.monitor_gate.MonitorGate (version, default "v2" = the final system; embedder, task,
    run_id). k and every other system setting come from src.monitor.case_inputs.VERSIONS[version] only. The agent loop hands the gate the live state before each write (MonitorGate.observe).
    Decisions: ALLOW applies; BLOCK / ESCALATE refuse and tell the agent the decision and the policy id;
    ASK_CONFIRMATION asks the user (yes applies, no refuses)."""
    from src.live.monitor_gate import MonitorGate
    return MonitorGate(model, setting=setting, **kwargs)
