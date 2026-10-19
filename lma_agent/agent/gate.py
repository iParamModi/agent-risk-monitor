"""Gates decide what happens to a write: allow_all and fake_gate now, the real monitor later."""
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


def run_monitor(messages: list[dict], call: ToolCall) -> GateDecision:
    """The real monitor (later); same signature as allow_all."""
    raise NotImplementedError("the monitor is not built yet")
