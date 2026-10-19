from lma_agent.sim.models import ToolCall
from lma_agent.tools.validate import validate_call


def call(name, **args):
    return ToolCall(id="c1", name=name, args=args)


def test_valid_calls():
    assert validate_call(call("delete_file", path="/project/report_7.pdf")) is None
    assert validate_call(call("read_inbox")) is None
    assert validate_call(call("transfer_money", from_account="A", to_account="B", amount=75000)) is None
    assert validate_call(call("write_cells", path="/f.xlsx", range="B4", values=[1200])) is None


def test_unknown_tool():
    assert validate_call(call("run_command", cmd="rm -rf /"))["error"] == "unknown_tool"


def test_missing_arg():
    err = validate_call(call("share_file", path="/a", permission="view"))
    assert err["error"] == "bad_args" and "recipient" in err["detail"]


def test_wrong_type_and_enum():
    assert validate_call(call("transfer_money", from_account="A", to_account="B", amount="lots"))["error"] == "bad_args"
    assert validate_call(call("grant_access", user_id="u", resource="r", role="owner"))["error"] == "bad_args"
    assert validate_call(call("send_email", to="x@y.com", subject="s", body="b"))["error"] == "bad_args"


def test_extra_or_raw_args_rejected():
    assert validate_call(call("delete_file", _raw="{bad json"))["error"] == "bad_args"
    assert validate_call(call("delete_file", path="/a", force=True))["error"] == "bad_args"
