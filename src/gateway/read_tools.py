"""Kept for old call sites: the check functions now live in src/gateway/checks.py and every call goes
through src/gateway/gateway.py (validation, write guard, errors as data)."""
from lma_agent.sim.models import CompanyState, ToolCall
from src.gateway.checks import CHECK_FUNCS  # noqa: F401
from src.gateway.gateway import call_check
from src.gateway.registry import CHECK_TOOLS_PATH

import yaml

CHECK_SPECS = yaml.safe_load(CHECK_TOOLS_PATH.read_text(encoding="utf-8"))


def run_check(state: CompanyState, call: ToolCall) -> dict:
    """Validate and run one check. Errors come back as data, never raised."""
    return call_check(state, call.name, call.args)
