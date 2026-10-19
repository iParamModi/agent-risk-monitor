import pytest

from lma_agent.agent.gate import allow_all, fake_gate, run_monitor
from lma_agent.sim.models import ToolCall

CALL = ToolCall(id="c", name="delete_file", args={"path": "/a"})


def test_allow_all():
    assert allow_all([], CALL).decision == "ALLOW"


@pytest.mark.parametrize("d", ["ALLOW", "ASK_CONFIRMATION", "BLOCK", "ESCALATE"])
def test_fake_gate(d):
    out = fake_gate(d)([], CALL)
    assert out.decision == d and out.policy_id == "P_TEST"


def test_monitor_not_built():
    with pytest.raises(NotImplementedError):
        run_monitor([], CALL)
