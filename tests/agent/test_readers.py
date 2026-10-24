from datetime import date

import pytest

from lma_agent.sim import readers
from lma_agent.sim.readers import NotFound
from lma_agent.sim.seed_state import build_seed_state

S = build_seed_state(0)


def test_file_readers():
    assert readers._get_file(S, "/project/report_7.pdf").owner == "u_riya"
    assert readers._get_file(S, "report_7.pdf").path == "/project/report_7.pdf"
    meta = readers._file_meta(S, "/finance/pricing_sheet.xlsx")
    assert meta == {"path": "/finance/pricing_sheet.xlsx", "folder": "/finance", "owner": "u_riya",
                    "sharing": "internal", "classification": "confidential", "modified": date(2026, 9, 12)}


def test_folder_sharing_is_inherited_from_nearest_folder():
    assert readers._folder_sharing(S, "/Partner_Share") == "external:globex"
    assert readers._folder_sharing(S, "/Public/sub") == "public"
    assert readers._folder_sharing(S, "/unlisted") == "internal"
    assert readers._effective_sharing(S, S.files["/hr/holiday_calendar_2026.pdf"]) == "public"  # own setting wins


def test_other_readers():
    assert readers._get_user(S, "u_dev").approval_limit_inr == 0
    assert readers._get_contact(S, "partner@globex.io").kind == "external"
    assert readers._get_contact(S, "c_globex").email == "partner@globex.io"
    assert readers._get_account(S, "ACC-OPS").balance_inr == 2500000
    assert readers._get_repo(S, "AcmePay").production is True


def test_unknown_contact_gets_org_from_domain():
    c = readers._get_contact(S, "nobody@evil.example")
    assert c.org == "evil.example" and c.kind == "external"
    assert readers._get_contact(S, "new.hire@acme.com").kind == "internal"


def test_recipient_scope():
    assert readers._recipient(S, "external_link") == ("external_link", "public")
    assert readers._recipient(S, "team_drive") == ("team_drive", "internal")
    assert readers._recipient(S, "u_kabir") == ("kabir@acme.com", "internal")
    assert readers._recipient(S, "c_globex") == ("partner@globex.io", "external:globex")
    assert readers._recipient(S, "x@other.example") == ("x@other.example", "external:other.example")


@pytest.mark.parametrize("fn,arg", [
    (readers._get_file, "/nope.pdf"), (readers._file_meta, "/nope.pdf"),
    (readers._get_user, "u_nobody"), (readers._get_account, "ACC-X"), (readers._get_repo, "nope"),
    (readers._get_contact, "c_nobody"),
])
def test_missing_raises_not_found(fn, arg):
    with pytest.raises(NotFound):
        fn(S, arg)


def test_resource_exists():
    assert readers._resource_exists(S, "AcmePay")
    assert readers._resource_exists(S, "/project")
    assert readers._resource_exists(S, "/project/report_7.pdf")
    assert readers._resource_exists(S, "/Partner_Share")  # listed folder without files
    assert not readers._resource_exists(S, "/nowhere")
