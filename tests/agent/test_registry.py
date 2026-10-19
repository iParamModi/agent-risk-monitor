from jsonschema import Draft202012Validator

from lma_agent.tools.registry import READ_TOOLS, SPECS, WRITE_TOOLS, get_agent_tool_schemas


def test_counts():
    assert len(SPECS) == 21
    assert len(READ_TOOLS) == 10 and len(WRITE_TOOLS) == 11
    assert {n for n, s in SPECS.items() if s.get("ood")} == {
        "get_customer_record", "archive_record", "export_customer_data"}
    assert all(s["phase"] == 1 for s in SPECS.values())


def test_schemas_are_openai_format_and_valid_json_schema():
    schemas = get_agent_tool_schemas(phase=1, include_ood=True)
    assert len(schemas) == 21
    for s in schemas:
        assert s["type"] == "function"
        fn = s["function"]
        assert set(fn) == {"name", "description", "parameters"}
        Draft202012Validator.check_schema(fn["parameters"])
        assert set(fn["parameters"]["required"]) <= set(fn["parameters"]["properties"])


def test_ood_filter():
    names = {s["function"]["name"] for s in get_agent_tool_schemas()}
    assert len(names) == 18 and "archive_record" not in names
    assert get_agent_tool_schemas(phase=0) == []
