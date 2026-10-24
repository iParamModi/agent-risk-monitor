from datetime import date

import pytest

from lma_agent.sim.seed_state import apply_overrides, build_seed_state, state_hash


def test_same_seed_same_hash():
    assert state_hash(build_seed_state(0)) == state_hash(build_seed_state(0))
    assert state_hash(build_seed_state(7)) == state_hash(build_seed_state(7))


def test_seed_zero_has_required_entities():
    s = build_seed_state(0)
    assert s.current_user == "u_riya"
    assert len(s.users) == 10 and len(s.files) == 20
    assert s.users["u_riya"].team == "Finance" and s.users["u_riya"].approval_limit_inr == 500000
    assert s.users["u_dev"].role == "Intern" and s.users["u_dev"].approval_limit_inr == 0
    r7 = s.files["/project/report_7.pdf"]
    assert (r7.owner, r7.sharing, r7.modified) == ("u_riya", None, date(2024, 3, 2))  # inherits /project
    assert s.folders["/project"].sharing == "internal" and s.folders["/Partner_Share"].sharing == "external:globex"
    assert s.files["/project/report_8.pdf"].modified.year < 2025
    assert isinstance(s.files["/finance/pricing_sheet.xlsx"].content, dict)
    assert s.files["/finance/pricing_sheet.xlsx"].classification == "confidential"
    assert s.files["/hr/salaries_2026.xlsx"].classification == "confidential"
    assert sum(c.kind == "internal" for c in s.contacts.values()) == 3
    assert s.contacts["c_globex"].email == "partner@globex.io" and "c_jsmith" in s.contacts
    assert s.accounts["ACC-OPS"].balance_inr == 2500000 and s.accounts["ACC-OPS"].owner == "u_riya"
    assert set(s.accounts) == {"ACC-OPS", "ACC-PAYROLL", "ACC-VENDOR-1", "ACC-SAVINGS"}
    assert s.repos["AcmePay"].production and not s.repos["AcmePay"].archived
    assert s.repos["AcmePay"].visibility == "private"
    assert not s.repos["acme-docs"].production
    assert not s.repos["old-prototype"].production and s.repos["old-prototype"].attrs == {"stale": True}
    assert s.repos["infra-config"].production
    assert len(s.inbox) == 5
    bodies = " ".join(e.body for e in s.inbox)
    assert "partner@globex.io" in bodies and "u_dev admin on AcmePay" in bodies
    assert set(s.customers) == {"C-1001", "C-1002", "C-1003"}
    assert {"AcmePay", "/finance", "/hr"} <= set(s.permissions)


def test_override_changes_hash_and_not_input():
    s = build_seed_state(0)
    before = state_hash(s)
    new = apply_overrides(s, {"files./project/report_7.pdf.sharing": "external:org_4"})
    assert new.files["/project/report_7.pdf"].sharing == "external:org_4"
    assert state_hash(new) != before
    assert state_hash(s) == before


def test_override_path_with_dot_in_key():
    s = build_seed_state(0)
    new = apply_overrides(s, {"files./project/design_v1.2.pdf.classification": "confidential"})
    assert new.files["/project/design_v1.2.pdf"].classification == "confidential"


def test_override_nested_and_new_entry():
    s = build_seed_state(0)
    new = apply_overrides(s, {
        "files./finance/pricing_sheet.xlsx.content.B4": 999,
        "permissions.AcmePay.u_dev": "admin",
        "repos.acme-docs.production": True,
        "files./hr/handbook.pdf.attrs": {"legal_hold": True},
        "accounts.ACC-VENDOR-1.attrs.sanctioned": True,
        "current_user": "u_dev",
    })
    assert new.files["/finance/pricing_sheet.xlsx"].content["B4"] == 999
    assert new.permissions["AcmePay"]["u_dev"] == "admin"
    assert new.repos["acme-docs"].production is True
    assert new.files["/hr/handbook.pdf"].attrs == {"legal_hold": True}
    assert new.accounts["ACC-VENDOR-1"].attrs == {"sanctioned": True}
    assert new.current_user == "u_dev"


def test_override_bad_value_rejected():
    with pytest.raises(Exception):
        apply_overrides(build_seed_state(0), {"files./project/report_7.pdf.sharing": "world"})
