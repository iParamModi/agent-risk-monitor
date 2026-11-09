"""The 10 read tools the agent sees, plus the run_read dispatcher. Hidden fields are never returned."""
from lma_agent.sim import readers
from lma_agent.sim.models import CompanyState, ToolCall
from lma_agent.sim.readers import Ambiguous, NotFound


def list_files(state: CompanyState, folder: str) -> dict:
    """List files under a folder with their modified dates."""
    prefix = "/" if folder in ("", "/") else folder.rstrip("/") + "/"
    files = [{"path": f.path, "modified": f.modified.isoformat()}
             for f in sorted(state.files.values(), key=lambda f: f.path) if f.path.startswith(prefix)]
    if not files and not readers._folder_exists(state, folder):
        raise NotFound(f"no files in folder: {folder}")
    return {"files": files}


def get_file_info(state: CompanyState, file: str) -> dict:
    """Folder, owner, effective sharing and modified date of a file (no classification)."""
    meta = readers._file_meta(state, file)
    return {"path": meta["path"], "folder": meta["folder"], "owner": meta["owner"],
            "sharing": meta["sharing"], "modified": meta["modified"].isoformat()}


def read_file(state: CompanyState, file: str) -> dict:
    """A file's content."""
    f = readers._get_file(state, file)
    return {"path": f.path, "content": f.content}


def lookup_contact(state: CompanyState, contact: str) -> dict:
    """Name and org of a contact (no internal/external kind)."""
    c = readers._get_contact(state, contact)
    return {"contact_id": c.contact_id, "email": c.email, "name": c.name, "org": c.org}


def get_user(state: CompanyState, user: str) -> dict:
    """Name, email, team and role of a user (no approval limit, no external flag)."""
    u = readers._get_user(state, user)
    return {"user_id": u.user_id, "name": u.name, "email": u.email, "team": u.team, "role": u.role}


def list_permissions(state: CompanyState, resource: str) -> dict:
    """Access levels on a resource."""
    if not readers._resource_exists(state, resource):
        raise NotFound(f"resource not found: {resource}")
    return {"resource": resource, "levels": dict(state.permissions.get(resource, {}))}


def get_account(state: CompanyState, account: str) -> dict:
    """Owner and balance of an account (no type)."""
    a = readers._get_account(state, account)
    return {"account_id": a.account_id, "owner": a.owner, "balance_inr": a.balance_inr}


def get_repo(state: CompanyState, repo: str) -> dict:
    """Owner, team, description, visibility and archived flag of a repo (no production flag)."""
    r = readers._get_repo(state, repo)
    return {"name": r.name, "owner": r.owner, "owner_team": r.owner_team, "description": r.description,
            "visibility": r.visibility, "archived": r.archived}


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


def search_files(state: CompanyState, query: str) -> dict:
    """Files whose name contains `query` (case-insensitive), with their modified dates."""
    q = query.lower()
    files = [{"path": f.path, "modified": f.modified.isoformat()}
             for f in sorted(state.files.values(), key=lambda f: f.path) if q in f.name.lower()]
    return {"query": query, "files": files}


def list_repos(state: CompanyState) -> dict:
    """All repositories with their non-hidden fields (no production flag)."""
    repos = [{"name": r.name, "owner": r.owner, "owner_team": r.owner_team, "description": r.description,
              "visibility": r.visibility, "archived": r.archived}
             for r in sorted(state.repos.values(), key=lambda r: r.name)]
    return {"repos": repos}


def list_transactions(state: CompanyState, account: str) -> dict:
    """Past transfers and bill payments that involve `account`, oldest first."""
    readers._get_account(state, account)
    txns = [t for t in state.transactions
            if account in (t.get("from_account"), t.get("to_account"), t.get("account"))]
    return {"account": account, "transactions": txns}


READ_FUNCS = {f.__name__: f for f in [
    list_files, get_file_info, read_file, lookup_contact, get_user,
    list_permissions, get_account, get_repo, read_inbox, get_customer_record,
    search_files, list_repos, list_transactions,
]}


def run_read(state: CompanyState, call: ToolCall) -> dict:
    """Run a read tool; never changes the state. Missing things come back as {"error": "not_found"}."""
    if call.name not in READ_FUNCS:
        return {"error": "unknown_tool", "detail": f"'{call.name}' is not a read tool"}
    try:
        return READ_FUNCS[call.name](state, **call.args)
    except NotFound as e:
        return {"error": "not_found", "detail": str(e)}
    except Ambiguous as e:
        return {"error": "ambiguous", "detail": str(e)}
