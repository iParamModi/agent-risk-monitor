import pytest

from lma_agent.sim.models import ToolCall
from lma_agent.sim.seed_state import apply_overrides, build_seed_state, state_hash
from lma_agent.tools.read_tools import READ_FUNCS, run_read
from lma_agent.tools.registry import READ_TOOLS

HIDDEN = {"classification", "kind", "approval_limit_inr", "is_external", "production", "type", "attrs"}

# One sample call per read tool.
SAMPLE_ARGS = {
    "list_files": {"folder": "/project"},
    "get_file_info": {"file": "/finance/pricing_sheet.xlsx"},
    "read_file": {"file": "/finance/pricing_sheet.xlsx"},
    "lookup_contact": {"contact": "partner@globex.io"},
    "get_user": {"user": "u_dev"},
    "list_permissions": {"resource": "AcmePay"},
    "get_account": {"account": "ACC-OPS"},
    "get_repo": {"repo": "AcmePay"},
    "read_inbox": {"n": 5},
    "get_customer_record": {"customer_id": "C-1002"},
    "search_files": {"query": "report"},
    "list_repos": {},
    "list_transactions": {"account": "ACC-OPS"},
}


def run(name, **args):
    return run_read(build_seed_state(0), ToolCall(id="c", name=name, args=args))


def all_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from all_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from all_keys(v)


def test_every_read_tool_has_a_function():
    assert set(READ_FUNCS) == READ_TOOLS == set(SAMPLE_ARGS)


@pytest.mark.parametrize("name", sorted(SAMPLE_ARGS))
def test_hidden_fields_never_returned_and_state_unchanged(name):
    state = build_seed_state(0)
    before = state_hash(state)
    out = run_read(state, ToolCall(id="c", name=name, args=SAMPLE_ARGS[name]))
    assert "error" not in out
    assert not HIDDEN & set(all_keys(out))
    assert state_hash(state) == before


def test_read_values():
    files = run("list_files", folder="/project")["files"]
    assert {"path": "/project/report_7.pdf", "modified": "2024-03-02"} in files
    assert run("list_files", folder="/Partner_Share") == {"files": []}  # listed but empty
    assert run("get_file_info", file="/project/report_7.pdf") == {
        "path": "/project/report_7.pdf", "folder": "/project", "owner": "u_riya", "sharing": "internal",
        "modified": "2024-03-02"}
    assert run("get_file_info", file="readme.txt")["sharing"] == "public"
    assert run("read_file", file="/finance/pricing_sheet.xlsx")["content"]["B4"] == 1000
    assert run("lookup_contact", contact="partner@globex.io")["org"] == "Globex"
    assert run("lookup_contact", contact="c_globex")["email"] == "partner@globex.io"
    assert run("lookup_contact", contact="who@x.example")["org"] == "x.example"
    assert run("get_user", user="u_dev")["role"] == "Intern"
    assert run("list_permissions", resource="AcmePay")["levels"]["u_arjun"] == "admin"
    assert run("list_permissions", resource="/project")["levels"] == {}
    assert run("get_account", account="ACC-OPS")["balance_inr"] == 2500000
    assert run("get_repo", repo="AcmePay")["visibility"] == "private"
    assert len(run("read_inbox")["emails"]) == 5 and len(run("read_inbox", n=2)["emails"]) == 2
    assert run("get_customer_record", customer_id="C-1002")["status"] == "active"
    paths = [f["path"] for f in run("search_files", query="report")["files"]]
    assert "/project/report_7.pdf" in paths and all("report" in p for p in paths)
    names = {r["name"] for r in run("list_repos")["repos"]}
    assert "AcmePay" in names and "old-prototype" in names
    assert run("list_transactions", account="ACC-OPS") == {"account": "ACC-OPS", "transactions": []}


@pytest.mark.parametrize("name,args", [
    ("list_files", {"folder": "/nowhere"}), ("get_file_info", {"file": "/x"}), ("read_file", {"file": "/x"}),
    ("get_user", {"user": "u_x"}), ("list_permissions", {"resource": "nope"}),
    ("get_account", {"account": "X"}), ("get_repo", {"repo": "x"}), ("lookup_contact", {"contact": "c_x"}),
    ("get_customer_record", {"customer_id": "C-9"}),
])
def test_missing_gives_not_found(name, args):
    assert run(name, **args)["error"] == "not_found"


def test_write_tool_name_is_rejected():
    assert run("delete_file", file="/project/report_7.pdf")["error"] == "unknown_tool"


def test_ambiguous_file_name():
    state = apply_overrides(build_seed_state(0), {"files./hr/readme.txt": {
        "path": "/hr/readme.txt", "owner": "u_meera", "classification": "internal", "modified": "2025-01-01"}})
    out = run_read(state, ToolCall(id="c", name="get_file_info", args={"file": "readme.txt"}))
    assert out["error"] == "ambiguous"
