"""Checks a tool call's name and arguments against the tool specs."""
from jsonschema import Draft202012Validator

from lma_agent.sim.models import ToolCall
from lma_agent.tools.registry import SPECS, args_schema


def validate_call(call: ToolCall, specs: dict = SPECS) -> dict | None:
    """Return None if the call is valid, else {"error": "unknown_tool" | "bad_args", "detail": ...}."""
    if call.name not in specs:
        return {"error": "unknown_tool", "detail": f"no tool named '{call.name}'"}
    validator = Draft202012Validator(args_schema(specs[call.name]))
    problems = [_describe(e) for e in validator.iter_errors(call.args)]
    if problems:
        return {"error": "bad_args", "detail": "; ".join(sorted(problems))}
    return None


def _describe(err) -> str:
    """Short readable text for one jsonschema error."""
    where = ".".join(str(p) for p in err.absolute_path)
    return f"{where}: {err.message}" if where else err.message
