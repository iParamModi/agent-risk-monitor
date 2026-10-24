"""Internal state readers. Never exposed to the LLM; shared with the monitor later."""
from lma_agent.sim.models import Account, CompanyState, Contact, File, Repo, User

INTERNAL_DOMAIN = "@acme.com"
DEFAULT_SHARING = "internal"  # a folder that is not listed counts as internal
PUBLIC_TARGETS = {"external_link", "public", "anyone"}
INTERNAL_TARGETS = {"team_drive", "general_drive", "internal"}


class NotFound(LookupError):
    """Raised when a path, id or name is not in the state."""


class Ambiguous(LookupError):
    """Raised when a bare file name matches more than one file."""


def _get_file(state: CompanyState, ref: str) -> File:
    """Return the file at path `ref`, or the only file named `ref`; else raise NotFound/Ambiguous."""
    if ref in state.files:
        return state.files[ref]
    hits = [f for f in state.files.values() if f.name == ref]
    if not hits:
        raise NotFound(f"file not found: {ref}")
    if len(hits) > 1:
        raise Ambiguous(f"more than one file named {ref}: {sorted(f.path for f in hits)}")
    return hits[0]


def _folder_sharing(state: CompanyState, folder: str) -> str:
    """Sharing of the nearest listed folder at or above `folder`."""
    path = folder.rstrip("/") or "/"
    while True:
        if path in state.folders:
            return state.folders[path].sharing
        if path == "/":
            return DEFAULT_SHARING
        path = path.rsplit("/", 1)[0] or "/"


def _effective_sharing(state: CompanyState, f: File) -> str:
    """The file's own sharing if set, else the one it inherits from its folder."""
    return f.sharing if f.sharing is not None else _folder_sharing(state, f.folder)


def _file_meta(state: CompanyState, ref: str) -> dict:
    """Return path, folder, owner, effective sharing, classification and modified date of a file."""
    f = _get_file(state, ref)
    return {"path": f.path, "folder": f.folder, "owner": f.owner, "sharing": _effective_sharing(state, f),
            "classification": f.classification, "modified": f.modified}


def _folder_exists(state: CompanyState, folder: str) -> bool:
    """True if `folder` is listed or holds files."""
    folder = folder.rstrip("/") or "/"
    prefix = "/" if folder == "/" else folder + "/"
    return folder in state.folders or any(p.startswith(prefix) for p in state.files)


def _get_user(state: CompanyState, user_id: str) -> User:
    """Return the user with `user_id` or raise NotFound."""
    if user_id not in state.users:
        raise NotFound(f"user not found: {user_id}")
    return state.users[user_id]


def _get_contact(state: CompanyState, ref: str) -> Contact:
    """Return the contact by id or email; an unknown email gets a contact built from its domain."""
    if ref in state.contacts:
        return state.contacts[ref]
    for c in state.contacts.values():
        if c.email.lower() == ref.lower():
            return c
    if "@" not in ref:
        raise NotFound(f"contact not found: {ref}")
    domain = ref.split("@", 1)[1].lower()
    internal = ref.lower().endswith(INTERNAL_DOMAIN)
    return Contact(contact_id=ref, email=ref, name="unknown", org="Acme Corp" if internal else domain,
                   kind="internal" if internal else "external")


def _recipient(state: CompanyState, ref: str) -> tuple[str, str]:
    """Return (address, sharing scope) for a user id, contact id, email or drive target.

    The scope is "internal", "public" or "external:<org>": what a file becomes when shared there.
    """
    if ref in PUBLIC_TARGETS:
        return ref, "public"
    if ref in INTERNAL_TARGETS:
        return ref, "internal"
    if ref in state.users:
        u = state.users[ref]
        return u.email, f"external:{u.team}" if u.is_external else "internal"
    c = _get_contact(state, ref)
    if c.kind == "external":
        return c.email, f"external:{c.org.lower().replace(' ', '_')}"
    return c.email, c.kind


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


def _resource_exists(state: CompanyState, resource: str) -> bool:
    """True if `resource` is a repo, a file, a folder, or already has access levels."""
    return (resource in state.permissions or resource in state.repos or resource in state.files
            or _folder_exists(state, resource))
