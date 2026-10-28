"""Rules only (never check): the if-then rules of src/baselines/rules.py over what is visible: the proposed
action, the user turns and the tool results shown in the conversation, gated by the 3 shown policies."""
from src.baselines.rules import decide, visible_facts


def run(record: dict, policies: list[dict]) -> tuple[dict, list[dict]]:
    """(the decision, the gateway calls made: none)."""
    return decide(record["visible"], policies, visible_facts(record["visible"])), []
