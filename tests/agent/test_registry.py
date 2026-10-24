import importlib.util
from pathlib import Path

from jsonschema import Draft202012Validator

from lma_agent.tools.registry import READ_TOOLS, SPECS, WRITE_TOOLS, get_agent_tool_schemas


def test_counts():
    assert len(SPECS) == 24
    assert len(READ_TOOLS) == 10 and len(WRITE_TOOLS) == 14
    assert {n for n, s in SPECS.items() if s.get("ood")} == {
        "get_customer_record", "archive_record", "export_customer_data"}
    assert {n for n, s in SPECS.items() if s["phase"] == 2} == {"create_event"}


def test_schemas_are_openai_format_and_valid_json_schema():
    schemas = get_agent_tool_schemas(phase=2, include_ood=True)
    assert len(schemas) == 24
    for s in schemas:
        assert s["type"] == "function"
        fn = s["function"]
        assert set(fn) == {"name", "description", "parameters"}
        Draft202012Validator.check_schema(fn["parameters"])
        assert set(fn["parameters"]["required"]) <= set(fn["parameters"]["properties"])


def test_ood_filter():
    names = {s["function"]["name"] for s in get_agent_tool_schemas()}
    assert len(names) == 20 and "archive_record" not in names and "create_event" not in names
    assert len(get_agent_tool_schemas(phase=2)) == 21
    assert get_agent_tool_schemas(phase=0) == []


def test_write_tools_match_seed_vocabulary():
    """The company's actions must take exactly the args the seeds use (scripts/check_seed_vocab.py)."""
    path = Path(__file__).resolve().parents[2] / "scripts" / "check_seed_vocab.py"
    spec = importlib.util.spec_from_file_location("check_seed_vocab", path)
    vocab = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vocab)
    assert set(vocab.ACTIONS) == WRITE_TOOLS
    for name, (required, optional) in vocab.ACTIONS.items():
        assert set(SPECS[name]["required"]) == required, name
        assert set(SPECS[name]["params"]) == required | optional, name
    for name, args in vocab.READS.items():
        assert set(SPECS[name]["required"]) == args, name
