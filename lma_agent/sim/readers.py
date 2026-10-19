"""Internal state readers. Never exposed to the LLM; shared with the monitor later."""
from lma_agent.sim.models import Account, CompanyState, Contact, File, Repo, User

INTERNAL_DOMAIN = "@acme.com"


class NotFound(LookupError):
    """Raised when a path, id or name is not in the state."""


def _get_file(state: CompanyState, path: str) -> File:
    """Return the file at `path` or raise NotFound."""
    if path not in state.files:
        raise NotFound(f"file not found: {path}")
    return state.files[path]


def _file_meta(state: CompanyState, path: str) -> dict:
    """Return owner, sharing, classification and modified date of a file."""
    f = _get_file(state, path)
    return {"owner": f.owner, "sharing": f.sharing, "classification": f.classification,
            "modified": f.modified}


def _get_user(state: CompanyState, user_id: str) -> User:
    """Return the user with `user_id` or raise NotFound."""
    if user_id not in state.users:
        raise NotFound(f"user not found: {user_id}")
    return state.users[user_id]


def _get_contact(state: CompanyState, email: str) -> Contact:
    """Return the contact for `email`; an unknown email gets org 'unknown'."""
    if email in state.contacts:
        return state.contacts[email]
    return Contact(email=email, name="unknown", org="unknown",
                   is_internal=email.lower().endswith(INTERNAL_DOMAIN))


def _get_account(state: CompanyState, account_id: str) -> Account:
    """Return the account or raise NotFound."""
    if account_id not in state.accounts:
        raise NotFound(f"account not found: {account_id}")
    return state.accounts[account_id]


def _get_repo(state: CompanyState, repo: str) -> Repo:
    """Return the repo or raise NotFound."""
    if repo not in state.repos:
        raise NotFound(f"repo not found: {repo}")
    return state.repos[repo]


def _is_internal_email(state: CompanyState, email: str) -> bool:
    """True if `email` belongs to Acme (known contact flag, else the domain)."""
    return _get_contact(state, email).is_internal


def _resource_exists(state: CompanyState, resource: str) -> bool:
    """True if `resource` is a repo, a file, a folder holding files, or already has roles."""
    if resource in state.permissions or resource in state.repos or resource in state.files:
        return True
    prefix = resource.rstrip("/") + "/"
    return any(p.startswith(prefix) for p in state.files)
