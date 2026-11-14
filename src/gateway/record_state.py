"""Build the simulator's CompanyState from a record's hidden state (for_record, decisions.md R7.2).

A record states only the facts its scenario needs. Each attribute goes into the matching typed simulator
field when it is one and its value fits, otherwise into the entity's `attrs` (read by checks.stated()
through configs/check_tools.yaml). Fields the record does not state keep the simulator's defaults, which
trigger no policy; required fields the record never states get neutral fillers below. Only
record["hidden"]["state"] is read, never gold.
"""
from datetime import date

from pydantic import ValidationError

from lma_agent.sim.models import Account, CompanyState, Contact, Customer, File, Folder, Repo, User

NO_LIMIT_INR = 1_000_000_000      # approval limit / balance nobody stated: large enough to trigger no policy
FILLER_DATE = date(2024, 1, 1)
LEVELS = {"read": "read", "viewer": "read", "write": "write", "editor": "write", "admin": "admin", "owner": "admin"}


def _build(model, base: dict, attrs: dict, record_id: str):
    """model(**base, typed attrs, attrs=rest). An attr whose value does not fit its typed field goes to attrs."""
    typed = {k: v for k, v in attrs.items() if k in model.model_fields and k not in base and k != "attrs"}
    extra = {k: v for k, v in attrs.items() if k not in typed}   # incl. a stated value whose base field got a filler
    while True:
        try:
            return model(**base, **typed, attrs=extra)
        except ValidationError as err:
            bad = {e["loc"][0] for e in err.errors() if e["loc"] and e["loc"][0] in typed}
            if not bad:
                raise ValueError(f"{record_id}: cannot build {model.__name__} from {base}: {err}") from err
            for k in bad:
                extra[k] = typed.pop(k)


def _rest(entry: dict, *drop: str) -> dict:
    return {k: v for k, v in entry.items() if k not in drop}


def state_from_record(record: dict, current_user: str) -> CompanyState:
    rid, st = record["record_id"], record["hidden"]["state"]

    users = {}
    for u in st.get("users", []):
        base = {"user_id": u["user_id"], "name": u["user_id"], "email": f"{u['user_id']}@northwind.example",
                "team": u.get("team", "unknown"), "role": u.get("role", "unknown"),
                "approval_limit_inr": u.get("approval_limit_inr", NO_LIMIT_INR)}
        users[u["user_id"]] = _build(User, base, _rest(u, *base), rid)
    if current_user not in users:
        users[current_user] = User(user_id=current_user, name=current_user, email=f"{current_user}@northwind.example",
                                   team="unknown", role="unknown", approval_limit_inr=NO_LIMIT_INR)

    folders, folder_paths = {}, {}
    for fo in st.get("folders", []):
        path = fo["path"].rstrip("/") or "/"
        folder_paths[fo.get("folder_id", path)] = path
        base = {"path": path, "sharing": fo.get("sharing", "internal")}
        try:
            folders[path] = _build(Folder, base, _rest(fo, "folder_id", "path", "sharing"), rid)
        except ValueError:      # a sharing value the simulator does not know: keep it as a stated fact
            folders[path] = _build(Folder, {"path": path, "sharing": "internal"},
                                   dict(_rest(fo, "folder_id", "path"), sharing=fo["sharing"]), rid)

    files = {}
    for f in st.get("files", []):
        name = f["file_id"]
        if name.startswith("/"):
            path = name
        else:
            folder = folder_paths.get(f.get("folder_id"), "")
            path = f"{folder.rstrip('/')}/{name}"
        base = {"path": path, "owner": f.get("owner", "unknown"),
                "classification": f.get("classification", "internal"),
                "modified": f.get("last_modified", FILLER_DATE)}
        attrs = _rest(f, "file_id", "folder_id", "owner", "classification", "last_modified")
        try:
            files[path] = _build(File, base, attrs, rid)
        except ValueError:      # classification outside the simulator's labels: keep it as a stated fact
            files[path] = _build(File, dict(base, classification="internal"),
                                 dict(attrs, classification=f["classification"]), rid)

    contacts = {}
    for c in st.get("contacts", []):
        ref = c.get("address") or c.get("email")
        base = {"contact_id": ref, "email": c.get("email", ref), "name": ref, "org": ref,
                "kind": c.get("kind", "external")}
        contacts[ref] = _build(Contact, base, _rest(c, "address", *base), rid)

    accounts = {}
    for a in st.get("accounts", []):
        base = {"account_id": a["account_id"], "owner": a.get("owner", "unknown"), "type": a.get("type", "internal"),
                "balance_inr": a.get("balance_inr", NO_LIMIT_INR)}
        accounts[a["account_id"]] = _build(Account, base, _rest(a, *base), rid)

    repos = {}
    for r in st.get("repositories", []):
        name = r.get("repo_id") or r["name"]
        base = {"name": name, "owner": r.get("owner_team", "unknown"), "owner_team": r.get("owner_team", "unknown"),
                "description": "", "visibility": "private", "production": r.get("production", False)}
        attrs = _rest(r, "repo_id", "name", *base)
        if "modifiable" in attrs:           # both repo checks read the same stated flag
            attrs.setdefault("status_modifiable", attrs["modifiable"])
        repos[name] = _build(Repo, base, attrs, rid)

    customers = {}
    for c in st.get("customer_records", []):
        base = {"customer_id": c["customer_id"], "name": c["customer_id"], "email": "", "data": {},
                "status": c.get("status", "active")}
        customers[c["customer_id"]] = _build(Customer, base, _rest(c, *base), rid)

    permissions = {res: {u: LEVELS.get(level, "read") for u, level in grants.items()}
                   for res, grants in (st.get("permissions") or {}).items()}

    return CompanyState(current_user=current_user, folders=folders, files=files, users=users, contacts=contacts,
                        permissions=permissions, accounts=accounts, repos=repos, inbox=[], customers=customers)
