from lma_agent.agent.user_sim import ScriptedUser
from lma_agent.sim.models import ToolCall

CALL = ToolCall(id="c", name="delete_file", args={"path": "/a"})


def test_scripted_user():
    yes, no = ScriptedUser(True), ScriptedUser(False)
    assert yes.confirm(CALL) is True and no.confirm(CALL) is False
    assert yes.asked == [CALL]
