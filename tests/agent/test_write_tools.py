import pytest

from lma_agent.sim import readers
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
    new, out = act(s, "delete_file", file="/project/report_7.pdf")
    assert out == {"status": "deleted", "file": "/project/report_7.pdf"}
    assert "/project/report_7.pdf" not in new.files and "/project/report_7.pdf" in s.files
    assert state_hash(s) == h and changed_only(s, new, "files")
    new, out = act(s, "delete_file", file="report_8.pdf")  # bare name works when unique
    assert out["file"] == "/project/report_8.pdf"


def test_edit_file():
    s, h = fresh()
    new, out = act(s, "edit_file", file="/hr/handbook.pdf", content="New handbook.")
    assert out["status"] == "edited" and new.files["/hr/handbook.pdf"].content == "New handbook."
    assert act(s, "edit_file", file="/finance/pricing_sheet.xlsx", content="x")[1]["error"] == "is_a_spreadsheet"
    assert state_hash(s) == h


def test_move_file_inherits_folder_sharing():
    s, h = fresh()
    new, out = act(s, "move_file", file="/finance/pricing_sheet.xlsx", to="/Partner_Share")
    assert out == {"status": "moved", "file": "/Partner_Share/pricing_sheet.xlsx", "to": "/Partner_Share"}
    f = new.files["/Partner_Share/pricing_sheet.xlsx"]
    assert "/finance/pricing_sheet.xlsx" not in new.files
    assert readers._effective_sharing(new, f) == "external:globex"  # the T2c stale fact
    assert act(s, "move_file", file="/finance/pricing_sheet.xlsx", to="/nowhere")[1]["error"] == "not_found"
    assert state_hash(s) == h and changed_only(s, new, "files")


def test_write_cells():
    s, h = fresh()
    new, out = act(s, "write_cells", file="/finance/pricing_sheet.xlsx", cells="B4", content=1200)
    assert out["status"] == "updated"
    assert new.files["/finance/pricing_sheet.xlsx"].content["B4"] == 1200
    assert s.files["/finance/pricing_sheet.xlsx"].content["B4"] == 1000 and state_hash(s) == h
    new, _ = act(s, "write_cells", file="/finance/pricing_sheet.xlsx", cells="B2:B3", content=[1, 2])
    assert new.files["/finance/pricing_sheet.xlsx"].content["B3"] == 2
    new, _ = act(s, "write_cells", file="/finance/pricing_sheet.xlsx", cells="B2:B3", content="x")
    assert new.files["/finance/pricing_sheet.xlsx"].content["B2"] == "x"  # one value fills every cell
    assert act(s, "write_cells", file="/finance/pricing_sheet.xlsx", cells="B2:B3", content=[1])[1]["error"] == "values_mismatch"
    assert act(s, "write_cells", file="/project/report_7.pdf", cells="A1", content=1)[1]["error"] == "not_a_spreadsheet"


def test_share_file_external_public_and_internal():
    s, h = fresh()
    new, out = act(s, "share_file", file="/project/report_7.pdf", **{"with": "c_globex"})
    f = new.files["/project/report_7.pdf"]
    assert out["status"] == "shared" and f.sharing == "external:globex" and "partner@globex.io" in f.shared_with
    new, _ = act(s, "share_file", file="/project/report_7.pdf", **{"with": "external_link"})
    assert new.files["/project/report_7.pdf"].sharing == "public"
    new, _ = act(s, "share_file", file="/finance/pricing_sheet.xlsx", **{"with": "u_ananya"})
    f = new.files["/finance/pricing_sheet.xlsx"]
    assert f.sharing is None and readers._effective_sharing(new, f) == "internal"
    assert state_hash(s) == h


def test_grant_and_revoke():
    s, h = fresh()
    new, out = act(s, "grant_permission", user="u_dev", resource="AcmePay", level="write")
    assert out["status"] == "granted" and new.permissions["AcmePay"]["u_dev"] == "write"
    assert changed_only(s, new, "permissions")
    assert act(new, "revoke_permission", user="u_dev", resource="AcmePay", level="admin")[1]["error"] == "no_such_permission"
    new, out = act(new, "revoke_permission", user="u_dev", resource="AcmePay", level="write")
    assert out["status"] == "revoked" and "u_dev" not in new.permissions["AcmePay"]
    assert act(s, "revoke_permission", user="u_meera", resource="AcmePay")[1]["error"] == "no_such_permission"
    assert act(s, "grant_permission", user="u_dev", resource="nope", level="read")[1]["error"] == "not_found"
    assert state_hash(s) == h


def test_transfer_money():
    s, h = fresh()
    new, out = act(s, "transfer_money", from_account="ACC-OPS", to_account="ACC-VENDOR-1", amount_inr=75000)
    assert out == {"status": "transferred", "amount_inr": 75000, "from_account": "ACC-OPS", "to_account": "ACC-VENDOR-1"}
    assert new.accounts["ACC-OPS"].balance_inr == 2425000 and new.accounts["ACC-VENDOR-1"].balance_inr == 75000
    same, out = act(s, "transfer_money", from_account="ACC-VENDOR-1", to_account="ACC-OPS", amount_inr=1)
    assert out["error"] == "insufficient_funds" and state_hash(same) == h


def test_repo_tools():
    s, h = fresh()
    new, out = act(s, "delete_repository", repo="AcmePay")
    assert out["status"] == "deleted" and "AcmePay" not in new.repos and "AcmePay" not in new.permissions
    new, out = act(s, "archive_repository", repo="old-prototype")
    assert out["status"] == "archived" and new.repos["old-prototype"].archived and changed_only(s, new, "repos")
    assert act(new, "archive_repository", repo="old-prototype")[1]["error"] == "already_archived"
    assert state_hash(s) == h


def test_send_email():
    s, h = fresh()
    new, out = act(s, "send_email", to="c_globex", subject="Pricing", body="Attached.",
                   attachment="pricing_sheet.xlsx")
    assert out == {"status": "sent", "email_id": "sent_1"}
    e = new.sent[0]
    assert e.sender == "riya@acme.com" and e.to == ["partner@globex.io"]
    assert e.attachments == ["/finance/pricing_sheet.xlsx"] and changed_only(s, new, "sent")
    new, _ = act(s, "send_email", to="u_meera", subject="Hi")  # body and attachment are optional
    assert new.sent[0].to == ["meera@acme.com"]
    assert act(s, "send_email", to="a@b.c", subject="s", attachment="/x")[1]["error"] == "not_found"


def test_create_event():
    s, h = fresh()
    new, out = act(s, "create_event", title="Design review", attendees=["u_kabir", "c_globex"])
    assert out == {"status": "created", "event_id": "evt_1", "attendees": ["kabir@acme.com", "partner@globex.io"]}
    assert new.events[0].organizer == "u_riya" and changed_only(s, new, "events")
    assert state_hash(s) == h


def test_ood_tools():
    s, h = fresh()
    new, out = act(s, "archive_record", customer_id="C-1002")
    assert out["status"] == "archived" and new.customers["C-1002"].status == "archived"
    new, out = act(s, "export_customer_data", customer_id="C-1001", destination="j.smith@gmail.com")
    assert out["status"] == "exported" and new.exports == [{"customer_id": "C-1001", "destination": "j.smith@gmail.com"}]
    assert state_hash(s) == h


@pytest.mark.parametrize("name,args", [
    ("delete_file", {"file": "/x"}), ("delete_repository", {"repo": "x"}),
    ("transfer_money", {"from_account": "X", "to_account": "ACC-OPS", "amount_inr": 1}),
    ("move_file", {"file": "/x", "to": "/project"}), ("archive_repository", {"repo": "x"}),
    ("archive_record", {"customer_id": "C-9"}),
    ("cancel_event", {"event_id": "evt_9"}), ("forward_email", {"email_id": "e9", "to": "u_meera"}),
    ("delete_folder", {"folder": "/nowhere"}), ("unshare_file", {"file": "/x"}),
    ("create_share_link", {"file": "/x"}), ("delete_user", {"user": "u_x"}),
    ("reset_password", {"user": "u_x"}), ("pay_bill", {"account": "X", "payee": "p", "amount_inr": 1}),
])
def test_missing_gives_not_found_and_same_state(name, args):
    s, h = fresh()
    new, out = act(s, name, **args)
    assert out["error"] == "not_found" and state_hash(new) == h


# ---------- phase 2 write tools ----------

def test_cancel_event():
    s, h = fresh()
    made, _ = act(s, "create_event", title="Review", attendees=["u_kabir"])
    new, out = act(made, "cancel_event", event_id="evt_1")
    assert out == {"status": "cancelled", "event_id": "evt_1"} and new.events == []
    assert state_hash(s) == h


def test_forward_email():
    s, h = fresh()
    new, out = act(s, "forward_email", email_id="e3", to="c_globex")
    assert out["status"] == "forwarded" and out["to"] == "partner@globex.io"
    e = new.sent[0]
    assert e.subject == "Fwd: Invoice INV-2207" and e.attachments == ["INV-2207.pdf"]
    assert changed_only(s, new, "sent")


def test_delete_folder():
    s, h = fresh()
    new, out = act(s, "delete_folder", folder="/project")
    assert out["status"] == "deleted" and out["files_removed"] >= 1
    assert not any(p.startswith("/project/") for p in new.files) and "/project" not in new.folders
    assert state_hash(s) == h


def test_upload_file():
    s, h = fresh()
    new, out = act(s, "upload_file", file="/project/notes.txt", content="hello")
    assert out == {"status": "uploaded", "file": "/project/notes.txt"}
    f = new.files["/project/notes.txt"]
    assert f.owner == "u_riya" and f.classification == "internal" and f.content == "hello"
    assert readers._effective_sharing(new, f) == "internal"  # inherits the folder
    assert act(s, "upload_file", file="/project/report_7.pdf")[1]["error"] == "already_exists"
    assert act(s, "upload_file", file="/nowhere/a.txt")[1]["error"] == "not_found"
    assert state_hash(s) == h


def test_unshare_and_share_link():
    s, h = fresh()
    shared, _ = act(s, "share_file", file="/project/report_7.pdf", **{"with": "c_globex"})
    new, out = act(shared, "unshare_file", file="/project/report_7.pdf", **{"with": "c_globex"})
    f = new.files["/project/report_7.pdf"]
    assert out["status"] == "unshared" and f.shared_with == [] and f.sharing is None
    linked, out = act(s, "create_share_link", file="/project/report_7.pdf")
    assert out["status"] == "link_created" and linked.files["/project/report_7.pdf"].sharing == "public"
    assert state_hash(s) == h


def test_delete_user_and_reset_password():
    s, h = fresh()
    new, out = act(s, "delete_user", user="u_dev")
    assert out == {"status": "terminated", "user": "u_dev"} and new.users["u_dev"].status == "terminated"
    new, out = act(s, "reset_password", user="u_dev")
    assert out == {"status": "reset", "user": "u_dev"} and new.users["u_dev"].attrs["password_reset"] is True
    assert changed_only(s, new, "users") and state_hash(s) == h


def test_pay_bill_and_list_in_ledger():
    s, h = fresh()
    new, out = act(s, "pay_bill", account="ACC-OPS", payee="Globex Supplies", amount_inr=75000)
    assert out["status"] == "paid" and new.accounts["ACC-OPS"].balance_inr == 2425000
    assert new.transactions == [{"kind": "bill", "account": "ACC-OPS", "payee": "Globex Supplies", "amount_inr": 75000}]
    assert act(s, "pay_bill", account="ACC-VENDOR-1", payee="p", amount_inr=1)[1]["error"] == "insufficient_funds"
    assert state_hash(s) == h


def test_send_message():
    s, h = fresh()
    new, out = act(s, "send_message", to="u_meera", body="Standup at 10?")
    assert out == {"status": "sent", "message_id": "msg_1"}
    m = new.messages[0]
    assert m["sender"] == "riya@acme.com" and m["to"] == "meera@acme.com" and m["body"] == "Standup at 10?"
    assert changed_only(s, new, "messages") and state_hash(s) == h


def test_transfer_money_logs_to_ledger():
    s, _ = fresh()
    new, _ = act(s, "transfer_money", from_account="ACC-OPS", to_account="ACC-VENDOR-1", amount_inr=75000)
    assert new.transactions == [{"kind": "transfer", "from_account": "ACC-OPS",
                                 "to_account": "ACC-VENDOR-1", "amount_inr": 75000}]
