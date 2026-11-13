"""The fictional company's state for the human viewer of a run: the first event's snapshot, the facts hidden from the
monitor, and the state after any step (snapshot + the run's state_diff events).

    company_snapshot(task, state)  -> payload of the company_snapshot event (run_agent emits it first)
    hidden_fields()                -> {collection: {field: {"checks": [...], "revealed_by": [...]}}}
    state_at(events, step)         -> the company state (JSON dict) after every state_diff up to that step

Hidden facts come from the gateway's own source of truth, configs/check_tools.yaml: a field is hidden from the
monitor when a check tool answers it (its `returns` or `facts`), for the collections that tool's resource param can
name. `revealed_by` lists the agent read tools that can also show it (the tool's own `revealed_by`). The snapshot is
for the HUMAN viewer only: it goes to the run log, never into the monitor's prompt (the monitor gets the visible
record of src/live/live_record.py and gateway results only; tests/test_company_state.py checks this).

No code here reads a CompanyState's fields one by one: the state is turned into a JSON dict first (model_dump), the
same dict the run log carries, so the gateway stays the monitor's only way into the environment.
"""
import copy
from functools import lru_cache

import yaml

from lma_agent.sim.models import Account, CompanyState, Contact, Customer, File, Folder, Repo, Task, User
from src.common.io import REPO_ROOT

CHECK_TOOLS = REPO_ROOT / "configs" / "check_tools.yaml"
MODELS = {"folders": Folder, "files": File, "users": User, "contacts": Contact, "accounts": Account,
          "repos": Repo, "customers": Customer}
# Which collections a check tool's resource param can name (src/gateway/checks.py: the readers each tool calls).
RESOURCE_COLLECTIONS = {
    "path": ("files", "folders"), "file": ("files",), "resource": ("files", "customers", "repos"),
    "user": ("users",), "recipient": ("contacts", "accounts", "users"), "account": ("accounts",),
    "to_account": ("accounts",), "repo": ("repos",), "customer_id": ("customers",),
}
# Whole collections only check tools read (check_owner_approval).
HIDDEN_COLLECTIONS = {"owner_approvals": ["check_owner_approval"]}
HIDDEN_ALWAYS = "attrs"          # per-entity hidden facts a record states (models.py: "hidden facts")


@lru_cache(maxsize=1)
def hidden_fields() -> dict[str, dict[str, dict]]:
    specs = yaml.safe_load(CHECK_TOOLS.read_text(encoding="utf-8"))
    out: dict[str, dict[str, dict]] = {c: {} for c in MODELS}
    for tool, spec in specs.items():
        params = set(spec.get("params") or {})
        names = (set(spec.get("returns") or {}) | set(spec.get("facts") or {})) - params
        revealed = [r.strip() for r in str(spec.get("revealed_by") or "none").split(",") if "." in r]
        for collection in RESOURCE_COLLECTIONS.get(spec.get("resource_param"), ()):
            fields = MODELS[collection].model_fields
            for name in sorted(names & set(fields)):
                entry = out[collection].setdefault(name, {"checks": [], "revealed_by": []})
                if tool not in entry["checks"]:
                    entry["checks"].append(tool)
                for r in revealed:
                    read_tool, field = r.split(".", 1)
                    if field == name and read_tool not in entry["revealed_by"]:
                        entry["revealed_by"].append(read_tool)
    for collection in MODELS:
        if HIDDEN_ALWAYS in MODELS[collection].model_fields:
            out[collection].setdefault(HIDDEN_ALWAYS, {"checks": [], "revealed_by": []})
    out.update({c: {"*": {"checks": tools, "revealed_by": []}} for c, tools in HIDDEN_COLLECTIONS.items()})
    return out


def company_snapshot(task: Task, state: CompanyState) -> dict:
    """Payload of the company_snapshot event: the full initial state and which facts the monitor cannot see."""
    return {"company": "Northwind Labs (fictional)", "task_id": task.task_id, "state_seed": task.state_seed,
            "overrides": dict(task.overrides or {}), "state": state.model_dump(mode="json"),
            "hidden_from_monitor": hidden_fields()}


def apply_diff(state: dict, diff: dict) -> dict:
    """The state dict after one state_diff payload (src.live.events.state_diff)."""
    out = copy.deepcopy(state)
    for ch in diff.get("changes", []):
        coll, key, kind = ch["collection"], ch["key"], ch["kind"]
        if kind == "replaced" or key == "":
            out[coll] = copy.deepcopy(ch["after"])
        elif isinstance(out.get(coll), list):
            out[coll].append(copy.deepcopy(ch["after"]))
        elif kind == "removed":
            out[coll].pop(key, None)
        else:
            out.setdefault(coll, {})[key] = copy.deepcopy(ch["after"])
    return out


def state_at(events: list[dict], step: int | None = None) -> dict:
    """{"step", "state", "hidden_from_monitor", "diffs"}: the company after every state_diff with step <= `step`
    (None = the end of the run)."""
    snap = next((e for e in events if e["type"] == "company_snapshot"), None)
    if snap is None:
        raise ValueError("this run log has no company_snapshot event (recorded before 13 Nov)")
    state, diffs = snap["payload"]["state"], []
    for e in events:
        if e["type"] == "state_diff" and (step is None or e["step"] <= step):
            state = apply_diff(state, e["payload"])
            diffs.append({"step": e["step"], "changes": e["payload"].get("changes", [])})
    return {"step": step, "state": state, "hidden_from_monitor": snap["payload"]["hidden_from_monitor"], "diffs": diffs}
