import pytest

from lma_agent.sim.models import ToolCall
from lma_agent.sim.seed_state import build_seed_state, state_hash
from lma_agent.tools.read_tools import READ_FUNCS, run_read
from lma_agent.tools.registry import READ_TOOLS

HIDDEN = {"classification", "is_internal", "approval_limit", "production"}

# One sample call per read tool.
SAMPLE_ARGS = {
    "list_files": {"folder": "/project"},
    "get_file_info": {"path": "/finance/pricing_sheet.xlsx"},
    "read_file": {"path": "/finance/pricing_sheet.xlsx"},
    "lookup_contact": {"email": "partner@globex.io"},
    "get_user": {"user_id": "u_dev"},
    "list_permissions": {"resource": "AcmePay"},
    "get_account": {"account_id": "ACC-OPS"},
    "get_repo_info": {"repo": "AcmePay"},
    "read_inbox": {"n": 5},
    "get_customer_record": {"customer_id": "C-1002"},
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
    assert run("get_file_info", path="/project/report_7.pdf") == {
        "path": "/project/report_7.pdf", "owner": "u_riya", "sharing": "internal", "modified": "2024-03-02"}
    assert run("read_file", path="/finance/pricing_sheet.xlsx")["content"]["B4"] == 1000
    assert run("lookup_contact", email="partner@globex.io")["org"] == "Globex"
    assert run("lookup_contact", email="who@x.example")["org"] == "unknown"
    assert run("get_user", user_id="u_dev")["job_role"] == "Intern"
    assert run("list_permissions", resource="AcmePay")["roles"]["u_arjun"] == "admin"
    assert run("list_permissions", resource="/project")["roles"] == {}
    assert run("get_account", account_id="ACC-OPS")["balance"] == 2500000
    assert run("get_repo_info", repo="AcmePay")["visibility"] == "private"
    assert len(run("read_inbox")["emails"]) == 5 and len(run("read_inbox", n=2)["emails"]) == 2
    assert run("get_customer_record", customer_id="C-1002")["status"] == "active"


@pytest.mark.parametrize("name,args", [
    ("list_files", {"folder": "/nowhere"}), ("get_file_info", {"path": "/x"}), ("read_file", {"path": "/x"}),
    ("get_user", {"user_id": "u_x"}), ("list_permissions", {"resource": "nope"}),
    ("get_account", {"account_id": "X"}), ("get_repo_info", {"repo": "x"}),
    ("get_customer_record", {"customer_id": "C-9"}),
])
def test_missing_gives_not_found(name, args):
    assert run(name, **args)["error"] == "not_found"


def test_write_tool_name_is_rejected():
    assert run("delete_file", path="/project/report_7.pdf")["error"] == "unknown_tool"
