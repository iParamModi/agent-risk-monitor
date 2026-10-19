"""The 10 read tools the agent sees, plus the run_read dispatcher. Hidden fields are never returned."""
from lma_agent.sim import readers
from lma_agent.sim.models import CompanyState, ToolCall
from lma_agent.sim.readers import NotFound


def list_files(state: CompanyState, folder: str) -> dict:
    """List files under a folder with their modified dates."""
    prefix = "/" if folder in ("", "/") else folder.rstrip("/") + "/"
    files = [{"path": f.path, "modified": f.modified.isoformat()}
             for f in sorted(state.files.values(), key=lambda f: f.path) if f.path.startswith(prefix)]
    if not files:
        raise NotFound(f"no files in folder: {folder}")
    return {"files": files}


def get_file_info(state: CompanyState, path: str) -> dict:
    """Owner, sharing and modified date of a file (no classification)."""
    meta = readers._file_meta(state, path)
    return {"path": path, "owner": meta["owner"], "sharing": meta["sharing"],
            "modified": meta["modified"].isoformat()}


def read_file(state: CompanyState, path: str) -> dict:
    """A file's content."""
    return {"path": path, "content": readers._get_file(state, path).content}


def lookup_contact(state: CompanyState, email: str) -> dict:
    """Name and org of a contact (no internal/external flag)."""
    c = readers._get_contact(state, email)
    return {"email": c.email, "name": c.name, "org": c.org}


def get_user(state: CompanyState, user_id: str) -> dict:
    """Name, team and job role of a user (no approval limit)."""
    u = readers._get_user(state, user_id)
    return {"user_id": u.user_id, "name": u.name, "team": u.team, "job_role": u.job_role}


def list_permissions(state: CompanyState, resource: str) -> dict:
    """Roles on a resource."""
    if not readers._resource_exists(state, resource):
        raise NotFound(f"resource not found: {resource}")
    return {"resource": resource, "roles": dict(state.permissions.get(resource, {}))}


def get_account(state: CompanyState, account_id: str) -> dict:
    """Owner and balance of an account."""
    a = readers._get_account(state, account_id)
    return {"account_id": a.account_id, "owner": a.owner, "balance": a.balance}


def get_repo_info(state: CompanyState, repo: str) -> dict:
    """Owner, description and visibility of a repo (no production flag)."""
    r = readers._get_repo(state, repo)
    return {"name": r.name, "owner": r.owner, "description": r.description, "visibility": r.visibility}


def read_inbox(state: CompanyState, n: int = 5) -> dict:
    """The n most recent inbox emails, newest first."""
    emails = list(reversed(state.inbox))[:n]
    return {"emails": [{"email_id": e.email_id, "from": e.sender, "subject": e.subject,
                        "body": e.body, "attachments": list(e.attachments)} for e in emails]}


def get_customer_record(state: CompanyState, customer_id: str) -> dict:
    """Name, email and status of a customer (OOD)."""
    if customer_id not in state.customers:
        raise NotFound(f"customer not found: {customer_id}")
    c = state.customers[customer_id]
    return {"customer_id": c.customer_id, "name": c.name, "email": c.email, "status": c.status}


READ_FUNCS = {f.__name__: f for f in [
    list_files, get_file_info, read_file, lookup_contact, get_user,
    list_permissions, get_account, get_repo_info, read_inbox, get_customer_record,
]}


def run_read(state: CompanyState, call: ToolCall) -> dict:
    """Run a read tool; never changes the state. Missing things come back as {"error": "not_found"}."""
    if call.name not in READ_FUNCS:
        return {"error": "unknown_tool", "detail": f"'{call.name}' is not a read tool"}
    try:
        return READ_FUNCS[call.name](state, **call.args)
    except NotFound as e:
        return {"error": "not_found", "detail": str(e)}
