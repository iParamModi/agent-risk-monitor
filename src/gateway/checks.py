"""check_* tools: one pure function per check, check_x(state, **args) -> dict. Read-only.

Every function reads the simulator's CompanyState, whether it came from the simulator (lma_agent) or from
a record (record_state.py builds the same object). A fact a record states under its own name is kept in
the entity's `attrs`; `stated()` reads it through the tool's facts map in configs/check_tools.yaml, so both
modes run the same code. Fields nobody stated keep the simulator's defaults, which trigger no policy.

Results are built in the order configs/check_tools.yaml declares the returns, so their JSON is the same
text in every mode. Unknown resources raise readers.NotFound; the gateway turns that into data.
"""
from lma_agent.sim import readers
from lma_agent.sim.models import CompanyState
from lma_agent.sim.readers import NotFound
from src.gateway.registry import REGISTRY

_UNSET = object()


class UnmappedFact(ValueError):
    """A record states a fact value that the tool's facts map cannot translate (fix check_tools.yaml)."""


def _lookup(values: dict, value):
    if value in values:
        return values[value]
    for key, out in values.items():          # YAML keys may be bools, record values strings, or the reverse
        if str(key).lower() == str(value).lower():
            return out
    if value in values.values():             # already in the tool's own words
        return value
    return _UNSET


def stated(entity, tool: str, field: str):
    """The value a record states for `field` of `tool` (entity.attrs through the facts map), else _UNSET."""
    attrs = getattr(entity, "attrs", None) or {}
    for fact, target in REGISTRY[tool].facts.items():
        if target["field"] != field or fact not in attrs:
            continue
        value = attrs[fact]
        if target["values"] is None:
            return value
        out = _lookup(target["values"], value)
        if out is _UNSET:
            raise UnmappedFact(f"{tool}: fact {fact}={value!r} has no value for `{field}` in check_tools.yaml")
        return out
    return _UNSET


def _pick(entity, tool: str, field: str, default):
    value = stated(entity, tool, field)
    return default if value is _UNSET else value


# ---------- FILE ----------

def check_file_sharing(state: CompanyState, path: str) -> dict:
    """Effective sharing of a file (own, else its folder's) or of a folder."""
    tool = "check_file_sharing"
    try:
        f = readers._get_file(state, path)
        sharing, ref = _pick(f, tool, "sharing", readers._effective_sharing(state, f)), f.path
    except NotFound:
        folder = path.rstrip("/") or "/"
        if not readers._folder_exists(state, folder):
            raise
        entity = state.folders.get(folder)
        sharing, ref = _pick(entity, tool, "sharing", readers._folder_sharing(state, folder)), folder
    return {"path": ref, "sharing": sharing, "shared_external": sharing != "internal"}


def check_file_owner(state: CompanyState, file: str) -> dict:
    """Owner of a file and whether it is the current user."""
    f = readers._get_file(state, file)
    owner = _pick(f, "check_file_owner", "owner", f.owner)
    return {"file": f.path, "owner": owner, "owned_by_current_user": owner == state.current_user}


def check_file_classification(state: CompanyState, file: str) -> dict:
    """Sensitivity label and DLP scan result of a file."""
    f = readers._get_file(state, file)
    return {"file": f.path,
            "classification": _pick(f, "check_file_classification", "classification", f.classification),
            "dlp_scan": _pick(f, "check_file_classification", "dlp_scan", f.dlp_scan)}


def check_file_lock(state: CompanyState, file: str) -> dict:
    f = readers._get_file(state, file)
    return {"file": f.path, "locked": _pick(f, "check_file_lock", "locked", f.locked)}


def check_file_pii(state: CompanyState, file: str) -> dict:
    f = readers._get_file(state, file)
    return {"file": f.path, "contains_pii": _pick(f, "check_file_pii", "contains_pii", f.contains_pii)}


def _file_or_customer(state: CompanyState, resource: str):
    if resource in state.customers:
        return resource, state.customers[resource]
    f = readers._get_file(state, resource)
    return f.path, f


def check_retention_status(state: CompanyState, resource: str) -> dict:
    """Retention hold of a file or customer record."""
    ref, e = _file_or_customer(state, resource)
    return {"resource": ref,
            "retention_hold": _pick(e, "check_retention_status", "retention_hold", e.retention_hold),
            "retain_until": _pick(e, "check_retention_status", "retain_until", e.retain_until)}


def check_legal_hold(state: CompanyState, resource: str) -> dict:
    """Legal hold of a file or customer record."""
    ref, e = _file_or_customer(state, resource)
    return {"resource": ref, "legal_hold": _pick(e, "check_legal_hold", "legal_hold", e.legal_hold)}


def check_owner_team(state: CompanyState, resource: str) -> dict:
    """Team that owns a repository or a file (a file without its own owner_team takes its owner's team)."""
    if resource in state.repos:
        r = state.repos[resource]
        return {"resource": r.name, "owner_team": _pick(r, "check_owner_team", "owner_team", r.owner_team)}
    f = readers._get_file(state, resource)
    team = f.owner_team or (state.users[f.owner].team if f.owner in state.users else "unknown")
    return {"resource": f.path, "owner_team": _pick(f, "check_owner_team", "owner_team", team)}


# ---------- ACC ----------

def check_user_authorization(state: CompanyState, user: str, resource: str) -> dict:
    """Role, access level on the resource, and account type of a user, or of a contact the resource would
    go to (share_file `with`, send_email `to`): a contact's role is `contact`, its type follows its kind."""
    tool = "check_user_authorization"
    level = state.permissions.get(resource, {}).get(user, "none")
    if user in state.users:
        e, role, account_type = state.users[user], state.users[user].role, state.users[user].account_type
    else:
        e = readers._get_contact(state, user)
        role, account_type = "contact", "employee" if e.kind == "internal" else "external_contractor"
    return {"user": user, "resource": resource, "role": _pick(e, tool, "role", role),
            "access_level": _pick(e, tool, "access_level", level),
            "account_type": _pick(e, tool, "account_type", account_type)}


def check_user_clearance(state: CompanyState, user: str) -> dict:
    tool = "check_user_clearance"
    u = readers._get_user(state, user)
    return {"user": u.user_id,
            "authorized_hr": _pick(u, tool, "authorized_hr", u.authorized_hr),
            "authorized_financial": _pick(u, tool, "authorized_financial", u.authorized_financial),
            "authorized_pii": _pick(u, tool, "authorized_pii", u.authorized_pii),
            "authorized_legal": _pick(u, tool, "authorized_legal", u.authorized_legal),
            "clearance": _pick(u, tool, "clearance", u.clearance)}


def check_owner_approval(state: CompanyState, user: str, resource: str) -> dict:
    """Has the resource owner approved this user's access? A missing entry counts as approved."""
    u = readers._get_user(state, user)
    default = state.owner_approvals.get(resource, {}).get(user, True)
    return {"user": u.user_id, "resource": resource,
            "owner_approved": _pick(u, "check_owner_approval", "owner_approved", default)}


def check_admin_count(state: CompanyState, user: str, resource: str) -> dict:
    """Number of admins on the resource and whether this user is the only one."""
    tool = "check_admin_count"
    u = readers._get_user(state, user)
    admins = sorted(x for x, level in state.permissions.get(resource, {}).items() if level == "admin")
    count, last = len(admins), admins == [user]
    stated_last = stated(u, tool, "is_last_admin")
    if stated_last is not _UNSET and stated_last != last:   # a record states the answer: keep the count consistent
        last, count = stated_last, 1 if stated_last else max(count, 2)
    return {"user": u.user_id, "resource": resource, "admin_count": _pick(u, tool, "admin_count", count),
            "is_last_admin": last}


# ---------- PRIV / CAL / FIN ----------

def check_recipient_type(state: CompanyState, recipient: str) -> dict:
    """internal / external / public for a user, contact or drive target; the account type for an account."""
    tool = "check_recipient_type"
    if recipient in readers.PUBLIC_TARGETS:
        kind = "public"
    elif recipient in readers.INTERNAL_TARGETS:
        kind = "internal"
    elif recipient in state.users:     # an external contractor or vendor account is outside the company too
        u = state.users[recipient]
        outside = u.is_external or u.account_type != "employee"
        kind = _pick(u, tool, "recipient_type", "external" if outside else "internal")
    elif recipient in state.accounts:
        a = state.accounts[recipient]
        kind = _pick(a, tool, "recipient_type", a.type)
    else:
        c = readers._get_contact(state, recipient)
        kind = _pick(c, tool, "recipient_type", c.kind)
    return {"recipient": recipient, "recipient_type": kind}


def check_recipient_nda(state: CompanyState, recipient: str) -> dict:
    c = readers._get_contact(state, recipient)
    return {"recipient": recipient, "nda_in_place": _pick(c, "check_recipient_nda", "nda_in_place", c.nda_in_place)}


def check_recipient_verification(state: CompanyState, recipient: str) -> dict:
    c = readers._get_contact(state, recipient)
    return {"recipient": recipient,
            "address_verified": _pick(c, "check_recipient_verification", "address_verified", c.address_verified)}


def check_recipient_region(state: CompanyState, recipient: str) -> dict:
    """Region of an account or contact, and whether it is domestic."""
    tool = "check_recipient_region"
    e = state.accounts[recipient] if recipient in state.accounts else readers._get_contact(state, recipient)
    return {"recipient": recipient, "region": _pick(e, tool, "region", e.region),
            "domestic": _pick(e, tool, "domestic", e.domestic)}


def check_approval_limit(state: CompanyState, user: str) -> dict:
    u = readers._get_user(state, user)
    return {"user": u.user_id,
            "approval_limit_inr": _pick(u, "check_approval_limit", "approval_limit_inr", u.approval_limit_inr)}


def check_account_balance(state: CompanyState, account: str) -> dict:
    a = readers._get_account(state, account)
    return {"account": a.account_id, "balance_inr": _pick(a, "check_account_balance", "balance_inr", a.balance_inr)}


def check_sanctions(state: CompanyState, account: str) -> dict:
    a = readers._get_account(state, account)
    return {"account": a.account_id, "sanctioned": _pick(a, "check_sanctions", "sanctioned", a.sanctioned)}


def check_transfer_compliance(state: CompanyState, to_account: str, amount_inr: int) -> dict:
    """KYC, pre-approval, dual approval and duplicate flag of a payment to this payee."""
    tool = "check_transfer_compliance"
    a = readers._get_account(state, to_account)
    return {"to_account": a.account_id, "amount_inr": amount_inr,
            "kyc_status": _pick(a, tool, "kyc_status", a.kyc_status),
            "payee_preapproved": _pick(a, tool, "payee_preapproved", a.payee_preapproved),
            "dual_approval_obtained": _pick(a, tool, "dual_approval_obtained", a.dual_approval_obtained),
            "duplicate_flag": _pick(a, tool, "duplicate_flag", a.duplicate_flag)}


# ---------- REPO ----------

def check_repository_status(state: CompanyState, repo: str) -> dict:
    """Production flag, modifiable flag and lifecycle of a repository."""
    tool = "check_repository_status"
    r = readers._get_repo(state, repo)
    return {"repo": r.name, "production": _pick(r, tool, "production", r.production),
            "modifiable": _pick(r, tool, "modifiable", r.status_modifiable),
            "lifecycle": _pick(r, tool, "lifecycle", r.lifecycle)}


def check_repository_activity(state: CompanyState, repo: str) -> dict:
    """Running deploys, open incidents and dependants of a repository."""
    tool = "check_repository_activity"
    r = readers._get_repo(state, repo)
    return {"repo": r.name,
            "has_active_deploys": _pick(r, tool, "has_active_deploys", r.has_active_deploys),
            "has_active_incidents": _pick(r, tool, "has_active_incidents", r.has_active_incidents),
            "has_open_dependencies": _pick(r, tool, "has_open_dependencies", r.has_open_dependencies)}


def check_repository_archived(state: CompanyState, repo: str) -> dict:
    r = readers._get_repo(state, repo)
    return {"repo": r.name, "archived": _pick(r, "check_repository_archived", "archived", r.archived)}


def check_repository_backup(state: CompanyState, repo: str) -> dict:
    r = readers._get_repo(state, repo)
    return {"repo": r.name, "backup_exists": _pick(r, "check_repository_backup", "backup_exists", r.backup_exists)}


def check_repository_compliance(state: CompanyState, repo: str) -> dict:
    tool = "check_repository_compliance"
    r = readers._get_repo(state, repo)
    return {"repo": r.name, "compliance_locked": _pick(r, tool, "compliance_locked", r.compliance_locked),
            "modifiable": _pick(r, tool, "modifiable", r.modifiable)}


# ---------- CUST (OOD) ----------

def _customer(state: CompanyState, customer_id: str):
    if customer_id not in state.customers:
        raise NotFound(f"customer not found: {customer_id}")
    return state.customers[customer_id]


def check_customer_consent(state: CompanyState, customer_id: str) -> dict:
    tool = "check_customer_consent"
    c = _customer(state, customer_id)
    return {"customer_id": c.customer_id, "export_consent": _pick(c, tool, "export_consent", c.export_consent),
            "consent_scope": _pick(c, tool, "consent_scope", c.consent_scope)}


def check_customer_flags(state: CompanyState, customer_id: str) -> dict:
    """Do-not-contact flag, dispute state and account status of a customer."""
    tool = "check_customer_flags"
    c = _customer(state, customer_id)
    return {"customer_id": c.customer_id, "dnc": _pick(c, tool, "dnc", c.dnc),
            "dispute": _pick(c, tool, "dispute", c.dispute),
            "account_status": _pick(c, tool, "account_status", c.status)}


CHECK_FUNCS = {name: obj for name, obj in globals().items() if name.startswith("check_") and callable(obj)}

_missing = sorted(set(REGISTRY) - set(CHECK_FUNCS))
if _missing:
    raise ImportError(f"check tools without a function in src/gateway/checks.py: {_missing}")
