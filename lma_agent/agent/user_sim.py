"""Scripted user that answers ASK_CONFIRMATION prompts."""
from lma_agent.sim.models import ToolCall


class ScriptedUser:
    """Always answers the same way; remembers what it was asked."""

    def __init__(self, confirms: bool):
        self.confirms = confirms
        self.asked: list[ToolCall] = []

    def confirm(self, call: ToolCall) -> bool:
        """Answer a confirmation request for `call`."""
        self.asked.append(call)
        return self.confirms
