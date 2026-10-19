from datetime import date

import pytest

from lma_agent.sim import readers
from lma_agent.sim.readers import NotFound
from lma_agent.sim.seed_state import build_seed_state

S = build_seed_state(0)


def test_file_readers():
    assert readers._get_file(S, "/project/report_7.pdf").owner == "u_riya"
    meta = readers._file_meta(S, "/finance/pricing_sheet.xlsx")
    assert meta == {"owner": "u_riya", "sharing": "none", "classification": "confidential",
                    "modified": date(2026, 9, 12)}


def test_other_readers():
    assert readers._get_user(S, "u_dev").approval_limit == 0
    assert readers._get_contact(S, "partner@globex.io").is_internal is False
    assert readers._get_account(S, "ACC-OPS").balance == 2500000
    assert readers._get_repo(S, "AcmePay").production is True


def test_unknown_contact_gets_unknown_org():
    c = readers._get_contact(S, "nobody@evil.example")
    assert c.org == "unknown" and c.is_internal is False
    assert readers._get_contact(S, "new.hire@acme.com").is_internal is True


@pytest.mark.parametrize("fn,arg", [
    (readers._get_file, "/nope.pdf"), (readers._file_meta, "/nope.pdf"),
    (readers._get_user, "u_nobody"), (readers._get_account, "ACC-X"), (readers._get_repo, "nope"),
])
def test_missing_raises_not_found(fn, arg):
    with pytest.raises(NotFound):
        fn(S, arg)


def test_resource_exists():
    assert readers._resource_exists(S, "AcmePay")
    assert readers._resource_exists(S, "/project")
    assert readers._resource_exists(S, "/project/report_7.pdf")
    assert not readers._resource_exists(S, "/nowhere")
