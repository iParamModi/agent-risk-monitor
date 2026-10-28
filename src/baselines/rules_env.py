"""Rules + environment (always check): every check of configs/check_table.yaml for the proposed action, through
the check gateway (the same calls as the monitor's always setting), then the if-then rules of
src/baselines/rules.py over the visible facts and the returned facts."""
from src.baselines.rules import decide, facts_from_result, visible_facts
from src.gateway.gateway import _requested_by, for_record, table_calls


def run(record: dict, policies: list[dict]) -> tuple[dict, list[dict]]:
    """(the decision, the gateway calls in the predictions.jsonl format)."""
    gateway = for_record(record, setting="always")
    current_user = _requested_by(record["seed_id"], record["set"])      # the acting user, never gold
    facts, calls = visible_facts(record["visible"]), []
    for tool, args in table_calls(record["visible"]["proposed_action"], current_user):
        result = gateway.call(tool, args)
        calls.append({"tool": tool, "args": args, "error": result.get("error")})
        facts += facts_from_result(result)
    return decide(record["visible"], policies, facts), calls
