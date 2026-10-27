"""configs/fact_checks.yaml is generated from configs/check_tools.yaml and must match it."""
import importlib.util

import yaml

from src.common.io import REPO_ROOT

_spec = importlib.util.spec_from_file_location("gen_fact_checks", REPO_ROOT / "scripts" / "gen_fact_checks.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)
CHECK_TOOLS = yaml.safe_load(gen.CHECK_TOOLS.read_text(encoding="utf-8"))


def test_fact_checks_is_up_to_date():
    assert gen.OUT.read_text(encoding="utf-8") == gen.render(CHECK_TOOLS), \
        "configs/fact_checks.yaml is out of date: run python scripts/gen_fact_checks.py"


def test_every_tool_maps_its_facts_to_real_fields():
    for tool, spec in CHECK_TOOLS.items():
        assert spec.get("facts"), f"{tool} has no facts map"
        assert spec["resource_param"] in spec["params"], tool


def test_account_type_has_two_tools():
    tools = {e["tool"] for e in gen.build(CHECK_TOOLS)["account_type"]}
    assert tools == {"check_recipient_type", "check_user_authorization"}
