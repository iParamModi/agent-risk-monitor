"""The 14 write tools, plus apply_action, which runs them on a deep copy of the state.

Each tool is (state, **args) -> (new_state, dict) and changes the state it is given,
so always call it through apply_action. Problems raise WriteError or NotFound.
"""
import re

from lma_agent.sim import readers
from lma_agent.sim.models import CompanyState, Email, Event, ToolCall
from lma_agent.sim.readers import Ambiguous, NotFound


class WriteError(Exception):
    """A write that can't be done; `code` becomes the "error" field."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code


CELL = re.compile(r"^([A-Z]+)(\d+)$")
# Tool args that are Python keywords get a trailing underscore in the function signature.
ARG_RENAMES = {"with": "with_"}


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


def delete_file(state: CompanyState, file: str) -> tuple[CompanyState, dict]:
    """Remove a file."""
    f = readers._get_file(state, file)
    del state.files[f.path]
    return state, {"status": "deleted", "file": f.path}


def edit_file(state: CompanyState, file: str, content: str = "") -> tuple[CompanyState, dict]:
    """Replace a document's text content."""
    f = readers._get_file(state, file)
    if isinstance(f.content, dict):
        raise WriteError("is_a_spreadsheet", f"{f.path} has cells; use write_cells")
    f.content = content
    return state, {"status": "edited", "file": f.path}


def move_file(state: CompanyState, file: str, to: str) -> tuple[CompanyState, dict]:
    """Move a file into folder `to`; it then inherits that folder's sharing."""
    f = readers._get_file(state, file)
    folder = to.rstrip("/") or "/"
    if not readers._folder_exists(state, folder):
        raise NotFound(f"folder not found: {to}")
    new_path = f"{folder.rstrip('/')}/{f.name}"
    if new_path in state.files:
        raise WriteError("already_exists", f"{new_path} already exists")
    del state.files[f.path]
    f.path = new_path
    state.files[new_path] = f
    return state, {"status": "moved", "file": new_path, "to": folder}


def write_cells(state: CompanyState, file: str, cells: str, content) -> tuple[CompanyState, dict]:
    """Write one value into every cell, or a list of values row by row."""
    f = readers._get_file(state, file)
    if not isinstance(f.content, dict):
        raise WriteError("not_a_spreadsheet", f"{f.path} has no cells")
    names = _cells(cells)
    values = content if isinstance(content, list) else [content] * len(names)
    if len(names) != len(values):
        raise WriteError("values_mismatch", f"cells {cells} has {len(names)} cells but {len(values)} values given")
    f.content.update(zip(names, values))
    return state, {"status": "updated", "file": f.path, "cells": cells}


def share_file(state: CompanyState, file: str, with_: str) -> tuple[CompanyState, dict]:
    """Share a file; it becomes public or external:<org> if the target is outside Acme."""
    f = readers._get_file(state, file)
    address, scope = readers._recipient(state, with_)
    if address not in f.shared_with:
        f.shared_with.append(address)
    if scope != "internal" and readers._effective_sharing(state, f) != "public":
        f.sharing = scope
    return state, {"status": "shared", "file": f.path, "with": address}


def send_email(state: CompanyState, to: str, subject: str, body: str = "",
               attachment: str | None = None) -> tuple[CompanyState, dict]:
    """Append an email from the current user to `sent`; an attachment must be an existing file."""
    address, _ = readers._recipient(state, to)
    attachments = [readers._get_file(state, attachment).path] if attachment else []
    email_id = f"sent_{len(state.sent) + 1}"
    sender = readers._get_user(state, state.current_user).email
    state.sent.append(Email(email_id=email_id, sender=sender, to=[address], subject=subject, body=body,
                            attachments=attachments))
    return state, {"status": "sent", "email_id": email_id}


def create_event(state: CompanyState, title: str, attendees: list[str]) -> tuple[CompanyState, dict]:
    """Add a calendar event organised by the current user."""
    invited = [readers._recipient(state, a)[0] for a in attendees]
    event_id = f"evt_{len(state.events) + 1}"
    state.events.append(Event(event_id=event_id, title=title, organizer=state.current_user, attendees=invited))
    return state, {"status": "created", "event_id": event_id, "attendees": invited}


def grant_permission(state: CompanyState, user: str, resource: str, level: str) -> tuple[CompanyState, dict]:
    """Give a user an access level on a resource."""
    readers._get_user(state, user)
    if not readers._resource_exists(state, resource):
        raise NotFound(f"resource not found: {resource}")
    state.permissions.setdefault(resource, {})[user] = level
    return state, {"status": "granted", "user": user, "resource": resource, "level": level}


def revoke_permission(state: CompanyState, user: str, resource: str,
                      level: str | None = None) -> tuple[CompanyState, dict]:
    """Remove a user's access on a resource (only if it is `level`, when given)."""
    levels = state.permissions.get(resource, {})
    if user not in levels or (level and levels[user] != level):
        raise WriteError("no_such_permission", f"{user} has no {level or 'access'} on {resource}")
    del levels[user]
    return state, {"status": "revoked", "user": user, "resource": resource}


def transfer_money(state: CompanyState, from_account: str, to_account: str,
                   amount_inr: int) -> tuple[CompanyState, dict]:
    """Move money between accounts; fails if the source has too little."""
    src, dst = readers._get_account(state, from_account), readers._get_account(state, to_account)
    amount_inr = int(amount_inr)
    if src.balance_inr < amount_inr:
        raise WriteError("insufficient_funds", f"{from_account} balance is {src.balance_inr}")
    src.balance_inr -= amount_inr
    dst.balance_inr += amount_inr
    return state, {"status": "transferred", "amount_inr": amount_inr, "from_account": from_account,
                   "to_account": to_account}


def delete_repository(state: CompanyState, repo: str) -> tuple[CompanyState, dict]:
    """Remove a repository and its access levels."""
    readers._get_repo(state, repo)
    del state.repos[repo]
    state.permissions.pop(repo, None)
    return state, {"status": "deleted", "repo": repo}


def archive_repository(state: CompanyState, repo: str) -> tuple[CompanyState, dict]:
    """Mark a repository archived."""
    r = readers._get_repo(state, repo)
    if r.archived:
        raise WriteError("already_archived", f"{repo} is already archived")
    r.archived = True
    return state, {"status": "archived", "repo": repo}


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
    delete_file, edit_file, move_file, write_cells, share_file, send_email, create_event,
    grant_permission, revoke_permission, transfer_money, delete_repository, archive_repository,
    archive_record, export_customer_data,
]}


def apply_action(state: CompanyState, call: ToolCall) -> tuple[CompanyState, dict]:
    """Run a write tool on a deep copy; on error the original state comes back unchanged."""
    if call.name not in WRITE_FUNCS:
        return state, {"error": "unknown_tool", "detail": f"'{call.name}' is not a write tool"}
    args = {ARG_RENAMES.get(k, k): v for k, v in call.args.items()}
    try:
        return WRITE_FUNCS[call.name](state.model_copy(deep=True), **args)
    except NotFound as e:
        return state, {"error": "not_found", "detail": str(e)}
    except Ambiguous as e:
        return state, {"error": "ambiguous", "detail": str(e)}
    except WriteError as e:
        return state, {"error": e.code, "detail": str(e)}
