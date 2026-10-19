"""The 11 write tools, plus apply_action, which runs them on a deep copy of the state.

Each tool is (state, **args) -> (new_state, dict) and changes the state it is given,
so always call it through apply_action. Problems raise WriteError or NotFound.
"""
import re

from lma_agent.sim import readers
from lma_agent.sim.models import CompanyState, Email, ToolCall
from lma_agent.sim.readers import NotFound


class WriteError(Exception):
    """A write that can't be done; `code` becomes the "error" field."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code


CELL = re.compile(r"^([A-Z]+)(\d+)$")


def _cells(cell_range: str) -> list[str]:
    """Expand 'B4' or 'B4:C5' into cell names, row by row."""
    start, _, end = cell_range.upper().replace("$", "").partition(":")
    end = end or start
    a, b = CELL.match(start), CELL.match(end)
    if not a or not b or len(a[1]) > 1 or len(b[1]) > 1:
        raise WriteError("bad_range", f"can't read range: {cell_range}")
    cols = [chr(c) for c in range(ord(a[1]), ord(b[1]) + 1)]
    rows = range(int(a[2]), int(b[2]) + 1)
    if not cols or not rows:
        raise WriteError("bad_range", f"empty range: {cell_range}")
    return [f"{c}{r}" for r in rows for c in cols]


def delete_file(state: CompanyState, path: str) -> tuple[CompanyState, dict]:
    """Remove a file."""
    readers._get_file(state, path)
    del state.files[path]
    return state, {"status": "deleted", "path": path}


def write_cells(state: CompanyState, path: str, range: str, values: list) -> tuple[CompanyState, dict]:
    """Write values into spreadsheet cells, row by row."""
    f = readers._get_file(state, path)
    if not isinstance(f.content, dict):
        raise WriteError("not_a_spreadsheet", f"{path} has no cells")
    cells = _cells(range)
    if len(cells) != len(values):
        raise WriteError("values_mismatch", f"range {range} has {len(cells)} cells but {len(values)} values given")
    f.content.update(zip(cells, values))
    return state, {"status": "updated", "path": path, "range": range}


def share_file(state: CompanyState, path: str, recipient: str, permission: str) -> tuple[CompanyState, dict]:
    """Share a file; sharing becomes external if the recipient is outside Acme."""
    f = readers._get_file(state, path)
    if recipient in state.users:  # a user id was given instead of an email
        recipient = state.users[recipient].email
    if recipient not in f.shared_with:
        f.shared_with.append(recipient)
    if not readers._is_internal_email(state, recipient):
        f.sharing = "external"
    elif f.sharing == "none":
        f.sharing = "internal"
    return state, {"status": "shared", "path": path, "recipient": recipient, "permission": permission}


def grant_access(state: CompanyState, user_id: str, resource: str, role: str) -> tuple[CompanyState, dict]:
    """Give a user a role on a resource."""
    readers._get_user(state, user_id)
    if not readers._resource_exists(state, resource):
        raise NotFound(f"resource not found: {resource}")
    state.permissions.setdefault(resource, {})[user_id] = role
    return state, {"status": "granted", "user_id": user_id, "resource": resource, "role": role}


def revoke_access(state: CompanyState, user_id: str, resource: str) -> tuple[CompanyState, dict]:
    """Remove a user's role on a resource."""
    roles = state.permissions.get(resource, {})
    if user_id not in roles:
        raise WriteError("no_such_role", f"{user_id} has no role on {resource}")
    del roles[user_id]
    return state, {"status": "revoked", "user_id": user_id, "resource": resource}


def transfer_money(state: CompanyState, from_account: str, to_account: str, amount: int) -> tuple[CompanyState, dict]:
    """Move money between accounts; fails if the source has too little."""
    src, dst = readers._get_account(state, from_account), readers._get_account(state, to_account)
    amount = int(amount)
    if src.balance < amount:
        raise WriteError("insufficient_funds", f"{from_account} balance is {src.balance}")
    src.balance -= amount
    dst.balance += amount
    return state, {"status": "transferred", "amount": amount, "from_account": from_account, "to_account": to_account}


def delete_repository(state: CompanyState, repo: str) -> tuple[CompanyState, dict]:
    """Remove a repository and its roles."""
    readers._get_repo(state, repo)
    del state.repos[repo]
    state.permissions.pop(repo, None)
    return state, {"status": "deleted", "repo": repo}


def set_repo_visibility(state: CompanyState, repo: str, visibility: str) -> tuple[CompanyState, dict]:
    """Make a repository public or private."""
    readers._get_repo(state, repo).visibility = visibility
    return state, {"status": "updated", "repo": repo, "visibility": visibility}


def send_email(state: CompanyState, to: list[str], subject: str, body: str,
               attachments: list[str] | None = None) -> tuple[CompanyState, dict]:
    """Append an email from the current user to `sent`; attachments must be existing files."""
    attachments = attachments or []
    for path in attachments:
        readers._get_file(state, path)
    email_id = f"sent_{len(state.sent) + 1}"
    sender = readers._get_user(state, state.current_user).email
    state.sent.append(Email(email_id=email_id, sender=sender, to=to, subject=subject, body=body,
                            attachments=attachments))
    return state, {"status": "sent", "email_id": email_id}


def archive_record(state: CompanyState, customer_id: str) -> tuple[CompanyState, dict]:
    """Set a customer's status to archived (OOD)."""
    if customer_id not in state.customers:
        raise NotFound(f"customer not found: {customer_id}")
    state.customers[customer_id].status = "archived"
    return state, {"status": "archived", "customer_id": customer_id}


def export_customer_data(state: CompanyState, customer_id: str, destination: str) -> tuple[CompanyState, dict]:
    """Log an export of a customer's full record to a destination (OOD)."""
    if customer_id not in state.customers:
        raise NotFound(f"customer not found: {customer_id}")
    state.exports.append({"customer_id": customer_id, "destination": destination})
    return state, {"status": "exported", "customer_id": customer_id, "destination": destination}


WRITE_FUNCS = {f.__name__: f for f in [
    delete_file, write_cells, share_file, grant_access, revoke_access, transfer_money,
    delete_repository, set_repo_visibility, send_email, archive_record, export_customer_data,
]}


def apply_action(state: CompanyState, call: ToolCall) -> tuple[CompanyState, dict]:
    """Run a write tool on a deep copy; on error the original state comes back unchanged."""
    if call.name not in WRITE_FUNCS:
        return state, {"error": "unknown_tool", "detail": f"'{call.name}' is not a write tool"}
    try:
        return WRITE_FUNCS[call.name](state.model_copy(deep=True), **call.args)
    except NotFound as e:
        return state, {"error": "not_found", "detail": str(e)}
    except WriteError as e:
        return state, {"error": e.code, "detail": str(e)}
