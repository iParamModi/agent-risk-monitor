"""Loads tools.yaml into tool specs, OpenAI-format schemas and the READ/WRITE name sets."""
from pathlib import Path

import yaml

TOOLS_PATH = Path(__file__).resolve().parent.parent / "tools.yaml"


def load_tool_specs(path: str | Path = TOOLS_PATH) -> dict[str, dict]:
    """Return {tool name: spec} from tools.yaml."""
    with open(path) as fh:
        return yaml.safe_load(fh)


def args_schema(spec: dict) -> dict:
    """Return the JSON schema for one tool's arguments."""
    return {
        "type": "object",
        "properties": spec.get("params", {}),
        "required": spec.get("required", []),
        "additionalProperties": False,
    }


def get_agent_tool_schemas(phase: int = 1, include_ood: bool = False) -> list[dict]:
    """Return the agent's tools in OpenAI function-calling format."""
    return [
        {"type": "function",
         "function": {"name": name, "description": spec["description"], "parameters": args_schema(spec)}}
        for name, spec in SPECS.items()
        if spec["phase"] <= phase and (include_ood or not spec.get("ood", False))
    ]


SPECS = load_tool_specs()
READ_TOOLS = {n for n, s in SPECS.items() if s["type"] == "read"}
WRITE_TOOLS = {n for n, s in SPECS.items() if s["type"] == "write"}
