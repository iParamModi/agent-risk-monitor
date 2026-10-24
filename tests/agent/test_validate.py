from lma_agent.sim.models import ToolCall
from lma_agent.tools.validate import validate_call


def call(name, **args):
    return ToolCall(id="c1", name=name, args=args)


def test_valid_calls():
    assert validate_call(call("delete_file", file="/project/report_7.pdf")) is None
    assert validate_call(call("read_inbox")) is None
    assert validate_call(call("transfer_money", from_account="A", to_account="B", amount_inr=75000)) is None
    assert validate_call(call("write_cells", file="/f.xlsx", cells="B4", content=1200)) is None
    assert validate_call(call("write_cells", file="/f.xlsx", cells="B4:B5", content=[1, 2])) is None
    assert validate_call(call("share_file", file="/a", **{"with": "c_globex"})) is None
    assert validate_call(call("send_email", to="u_meera", subject="s")) is None


def test_unknown_tool():
    assert validate_call(call("run_command", cmd="rm -rf /"))["error"] == "unknown_tool"


def test_missing_arg():
    err = validate_call(call("share_file", file="/a"))
    assert err["error"] == "bad_args" and "with" in err["detail"]


def test_wrong_type_and_enum():
    assert validate_call(call("transfer_money", from_account="A", to_account="B", amount_inr="lots"))["error"] == "bad_args"
    assert validate_call(call("grant_permission", user="u", resource="r", level="owner"))["error"] == "bad_args"
    assert validate_call(call("send_email", to=["x@y.com"], subject="s"))["error"] == "bad_args"
    assert validate_call(call("create_event", title="t", attendees="u_kabir"))["error"] == "bad_args"


def test_extra_or_raw_args_rejected():
    assert validate_call(call("delete_file", _raw="{bad json"))["error"] == "bad_args"
    assert validate_call(call("delete_file", file="/a", force=True))["error"] == "bad_args"
