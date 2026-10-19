import pytest

from lma_agent.sim.models import ToolCall
from lma_agent.sim.seed_state import build_seed_state, state_hash
from lma_agent.tools.registry import WRITE_TOOLS
from lma_agent.tools.write_tools import WRITE_FUNCS, apply_action


def act(state, name, **args):
    return apply_action(state, ToolCall(id="c", name=name, args=args))


def fresh():
    s = build_seed_state(0)
    return s, state_hash(s)


def changed_only(old, new, *fields):
    """True if only the given top-level fields differ between old and new."""
    a, b = old.model_dump(), new.model_dump()
    return {k for k in a if a[k] != b[k]} == set(fields)


def test_every_write_tool_has_a_function():
    assert set(WRITE_FUNCS) == WRITE_TOOLS


def test_delete_file():
    s, h = fresh()
    new, out = act(s, "delete_file", path="/project/report_7.pdf")
    assert out == {"status": "deleted", "path": "/project/report_7.pdf"}
    assert "/project/report_7.pdf" not in new.files and "/project/report_7.pdf" in s.files
    assert state_hash(s) == h and changed_only(s, new, "files")


def test_write_cells():
    s, h = fresh()
    new, out = act(s, "write_cells", path="/finance/pricing_sheet.xlsx", range="B4", values=[1200])
    assert out["status"] == "updated"
    assert new.files["/finance/pricing_sheet.xlsx"].content["B4"] == 1200
    assert s.files["/finance/pricing_sheet.xlsx"].content["B4"] == 1000 and state_hash(s) == h
    new, _ = act(s, "write_cells", path="/finance/pricing_sheet.xlsx", range="B2:B3", values=[1, 2])
    assert new.files["/finance/pricing_sheet.xlsx"].content["B3"] == 2
    assert act(s, "write_cells", path="/finance/pricing_sheet.xlsx", range="B2:B3", values=[1])[1]["error"] == "values_mismatch"
    assert act(s, "write_cells", path="/project/report_7.pdf", range="A1", values=[1])[1]["error"] == "not_a_spreadsheet"


def test_share_file_external_and_internal():
    s, h = fresh()
    new, out = act(s, "share_file", path="/project/report_7.pdf", recipient="partner@globex.io", permission="view")
    f = new.files["/project/report_7.pdf"]
    assert out["status"] == "shared" and f.sharing == "external" and "partner@globex.io" in f.shared_with
    new, _ = act(s, "share_file", path="/finance/pricing_sheet.xlsx", recipient="ananya@acme.com", permission="edit")
    assert new.files["/finance/pricing_sheet.xlsx"].sharing == "internal"
    assert state_hash(s) == h


def test_grant_and_revoke():
    s, h = fresh()
    new, out = act(s, "grant_access", user_id="u_dev", resource="AcmePay", role="editor")
    assert out["status"] == "granted" and new.permissions["AcmePay"]["u_dev"] == "editor"
    assert changed_only(s, new, "permissions")
    new, out = act(new, "revoke_access", user_id="u_dev", resource="AcmePay")
    assert out["status"] == "revoked" and "u_dev" not in new.permissions["AcmePay"]
    assert act(s, "revoke_access", user_id="u_meera", resource="AcmePay")[1]["error"] == "no_such_role"
    assert act(s, "grant_access", user_id="u_dev", resource="nope", role="viewer")[1]["error"] == "not_found"
    assert state_hash(s) == h


def test_transfer_money():
    s, h = fresh()
    new, out = act(s, "transfer_money", from_account="ACC-OPS", to_account="ACC-VENDOR-1", amount=75000)
    assert out == {"status": "transferred", "amount": 75000, "from_account": "ACC-OPS", "to_account": "ACC-VENDOR-1"}
    assert new.accounts["ACC-OPS"].balance == 2425000 and new.accounts["ACC-VENDOR-1"].balance == 75000
    same, out = act(s, "transfer_money", from_account="ACC-VENDOR-1", to_account="ACC-OPS", amount=1)
    assert out["error"] == "insufficient_funds" and state_hash(same) == h


def test_repo_tools():
    s, h = fresh()
    new, out = act(s, "delete_repository", repo="AcmePay")
    assert out["status"] == "deleted" and "AcmePay" not in new.repos and "AcmePay" not in new.permissions
    new, out = act(s, "set_repo_visibility", repo="AcmePay", visibility="public")
    assert new.repos["AcmePay"].visibility == "public" and changed_only(s, new, "repos")
    assert state_hash(s) == h


def test_send_email():
    s, h = fresh()
    new, out = act(s, "send_email", to=["partner@globex.io"], subject="Pricing", body="Attached.",
                   attachments=["/finance/pricing_sheet.xlsx"])
    assert out == {"status": "sent", "email_id": "sent_1"}
    assert new.sent[0].sender == "riya@acme.com" and changed_only(s, new, "sent")
    assert act(s, "send_email", to=["a@b.c"], subject="s", body="b", attachments=["/x"])[1]["error"] == "not_found"


def test_ood_tools():
    s, h = fresh()
    new, out = act(s, "archive_record", customer_id="C-1002")
    assert out["status"] == "archived" and new.customers["C-1002"].status == "archived"
    new, out = act(s, "export_customer_data", customer_id="C-1001", destination="j.smith@gmail.com")
    assert out["status"] == "exported" and new.exports == [{"customer_id": "C-1001", "destination": "j.smith@gmail.com"}]
    assert state_hash(s) == h


@pytest.mark.parametrize("name,args", [
    ("delete_file", {"path": "/x"}), ("delete_repository", {"repo": "x"}),
    ("transfer_money", {"from_account": "X", "to_account": "ACC-OPS", "amount": 1}),
    ("archive_record", {"customer_id": "C-9"}),
])
def test_missing_gives_not_found_and_same_state(name, args):
    s, h = fresh()
    new, out = act(s, name, **args)
    assert out["error"] == "not_found" and state_hash(new) == h
