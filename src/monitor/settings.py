"""never / always / selective / oracle (decisions.md R9.5, PLAN Step 14.2) and the loop limits (R9.4)."""

SETTINGS = ("never", "always", "selective", "oracle")

MAX_PASSES = 3            # first pass, retry after a tool error, second pass
MAX_GATEWAY_CALLS = 4     # selective only; always/oracle run their fixed check list
MAX_CHECKS_PER_REQUEST = 2
MAX_REASON_WORDS = 30
DECIDE_NOW = "No checks are available. Decide now."   # never: the one re-prompt (PLAN 2.7)


def checks_before_pass(setting: str, action: dict, check_table: dict, gold: dict) -> list[dict]:
    """Checks the loop runs before the first model pass: all table checks (always), the gold checks
    (oracle), none otherwise. gold is read here only to pick the oracle checks; it never reaches the prompt.

    check_table maps an action name to [{"tool": <check tool>, "args": {<tool arg>: <action arg name>}}];
    the args are filled from the proposed action. A table arg missing from the action is left out
    (the gateway then answers invalid_args, which counts as a call, R7.6).
    """
    if setting == "always":
        out = []
        for entry in check_table.get(action["name"], []):
            args = {k: action["args"][v] for k, v in entry.get("args", {}).items() if v in action["args"]}
            out.append({"tool": entry["tool"], "args": args})
        return out
    if setting == "oracle":
        return [{"tool": c["tool"], "args": dict(c["args"])} for c in (gold.get("required_checks") or [])]
    return []
