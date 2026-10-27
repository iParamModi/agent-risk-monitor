"""The check-tool list the monitor sees (R7.1), from configs/check_tools.yaml, in the form render_tools expects.

Only names, arguments and return fields reach the prompt: `revealed_by` and `domain` are for the trust rule and
the coverage report. OOD-only tools (ood: true) are listed only for OOD runs, so in-domain training and
evaluation never show them.
"""
from pathlib import Path

import yaml

from src.common.io import REPO_ROOT

CHECK_TOOLS = REPO_ROOT / "configs" / "check_tools.yaml"


def load_check_tools(include_ood: bool = False, path: Path = CHECK_TOOLS) -> list[dict]:
    """[{"name", "args": {arg: description}, "returns": "{field: type, ...}"}] in file order."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    tools = []
    for name, spec in raw.items():
        if spec.get("ood") and not include_ood:
            continue
        returns = ", ".join(f"{k}: {v}" for k, v in spec.get("returns", {}).items())
        tools.append({"name": name, "args": {a: p.get("description", p.get("type", "")) for a, p in spec["params"].items()},
                      "returns": "{" + returns + "}"})
    return tools
