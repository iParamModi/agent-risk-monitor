import pytest

from lma_agent.agent.gate import allow_all, fake_gate, monitor_gate
from lma_agent.sim.models import ToolCall

CALL = ToolCall(id="c", name="delete_file", args={"path": "/a"})


def test_allow_all():
    assert allow_all([], CALL).decision == "ALLOW"


@pytest.mark.parametrize("d", ["ALLOW", "ASK_CONFIRMATION", "BLOCK", "ESCALATE"])
def test_fake_gate(d):
    out = fake_gate(d)([], CALL)
    assert out.decision == d and out.policy_id == "P_TEST"


def test_monitor_gate_needs_the_live_state():
    from src.live.fake_monitor import RuleFakeMonitor
    from src.live.monitor_gate import KeywordOnlyEmbedder
    gate = monitor_gate(RuleFakeMonitor(), embedder=KeywordOnlyEmbedder())
    with pytest.raises(RuntimeError, match="live state"):
        gate([], CALL)
