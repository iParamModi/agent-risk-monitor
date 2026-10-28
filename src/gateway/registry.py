"""Check tool registry: configs/check_tools.yaml is the single source of truth (decisions.md R7.1, R7.2).

Each tool: argument schema (same style as lma_agent/tools.yaml), the param that names its resource,
its returns fields with types, the allowed values of its category fields (enums), the facts map
(record fact -> returns field) and whether it is OOD-only.
The registry refuses to load if configs/check_table.yaml or configs/fact_checks.yaml names a tool that is
not here, or if a returns field has no known type.
"""
from dataclasses import dataclass
from pathlib import Path

import yaml

from lma_agent.tools.registry import WRITE_TOOLS, args_schema

ROOT = Path(__file__).resolve().parents[2]
CHECK_TOOLS_PATH = ROOT / "configs" / "check_tools.yaml"
CHECK_TABLE_PATH = ROOT / "configs" / "check_table.yaml"
FACT_CHECKS_PATH = ROOT / "configs" / "fact_checks.yaml"

RETURN_TYPES = {"string": str, "boolean": bool, "integer": int}
# Returns fields the simulator may leave unset (None = not recorded, models.py).
NULLABLE = {("check_repository_status", "lifecycle"), ("check_retention_status", "retain_until")}

# Any action the agent can apply is refused by the gateway (R7.4).
WRITE_ACTIONS = frozenset(WRITE_TOOLS)


@dataclass(frozen=True)
class Tool:
    name: str
    params: dict
    required: tuple
    schema: dict
    returns: dict            # field -> type name, in the order the result is built
    resource_param: str
    facts: dict              # record fact -> {"field", "values"}
    ood: bool
    enums: dict = None       # string returns field -> allowed values


def _facts(raw: dict) -> dict:
    out = {}
    for fact, target in (raw or {}).items():
        if isinstance(target, str):
            out[fact] = {"field": target, "values": None}
        else:
            out[fact] = {"field": target["field"], "values": target.get("values")}
    return out


def load_registry(path: Path = CHECK_TOOLS_PATH, table_path: Path = CHECK_TABLE_PATH,
                  fact_checks_path: Path = FACT_CHECKS_PATH) -> dict[str, Tool]:
    specs = yaml.safe_load(path.read_text(encoding="utf-8"))
    tools = {}
    for name, spec in specs.items():
        bad = {f: t for f, t in spec["returns"].items() if t not in RETURN_TYPES}
        if bad:
            raise ValueError(f"{name}: returns fields without a known type: {bad}")
        facts = _facts(spec.get("facts"))
        unknown = {f: t["field"] for f, t in facts.items() if t["field"] not in spec["returns"]}
        if unknown:
            raise ValueError(f"{name}: facts map to fields it does not return: {unknown}")
        enums = {f: tuple(v) for f, v in (spec.get("enums") or {}).items()}
        not_str = sorted(f for f in enums if spec["returns"].get(f) != "string")
        if not_str:
            raise ValueError(f"{name}: enums on fields that are not string returns: {not_str}")
        tools[name] = Tool(name=name, params=spec["params"], required=tuple(spec.get("required", [])),
                           schema=args_schema(spec), returns=dict(spec["returns"]),
                           resource_param=spec["resource_param"], facts=facts, ood=bool(spec.get("ood")),
                           enums=enums)
    table = yaml.safe_load(table_path.read_text(encoding="utf-8")) or {}
    missing = sorted({e["check"] for row in table.values() for e in (row or [])} - set(tools))
    if missing:
        raise ValueError(f"{table_path.name} names unknown check tools: {missing}")
    if fact_checks_path.exists():
        fact_checks = yaml.safe_load(fact_checks_path.read_text(encoding="utf-8")) or {}
        missing = sorted({e["tool"] for rows in fact_checks.values() for e in rows} - set(tools))
        if missing:
            raise ValueError(f"{fact_checks_path.name} names unknown check tools: {missing}")
    return tools


def check_types(tool: Tool, result: dict) -> None:
    """Raise if a check function broke its declared returns (a bug in our code, not a monitor error)."""
    if list(result) != list(tool.returns):
        raise TypeError(f"{tool.name} returned fields {list(result)}, declared {list(tool.returns)}")
    for field, type_name in tool.returns.items():
        value = result[field]
        if value is None and (tool.name, field) in NULLABLE:
            continue
        want = RETURN_TYPES[type_name]
        ok = isinstance(value, want) and not (want is int and isinstance(value, bool))
        if not ok:
            raise TypeError(f"{tool.name}.{field} = {value!r} is not {type_name}")
        if field in tool.enums and value not in tool.enums[field]:
            raise TypeError(f"{tool.name}.{field} = {value!r} is not one of {list(tool.enums[field])}")


REGISTRY = load_registry()
