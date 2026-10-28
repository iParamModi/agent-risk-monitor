"""The check gateway: the only path from the monitor (every setting and baseline) to the environment state.

    gateway = for_record(record)          # reads record["hidden"], record["set"], the proposed action; never gold
    result = gateway.call(tool, args)     # always a dict; errors are data (decisions.md R7.3, R7.4)

Four jobs, in this order, stopping at the first failure:
  1. write guard: any agent action -> {"error": "write_not_allowed"}, never run (R7.4)
  2. only approved check tools (OOD-only tools only on OOD records) -> {"error": "unknown_tool", "allowed": [...]}
  3. argument schema, then the resource must exist -> {"error": "invalid_args", ...} / {"error": "not_found", ...}
  4. run the check, count and log the call (R7.6: every call counts, errors included)

It never chooses a tool, adds a missing check or judges a call; the monitor does that and is scored later.
Error messages come from the fixed templates below and name only what the call itself sent.
"""
import json
from pathlib import Path
from typing import Literal

import yaml
from jsonschema import Draft202012Validator
from pydantic import BaseModel

from lma_agent.sim.models import CompanyState
from lma_agent.sim.readers import Ambiguous, NotFound
from src.gateway.checks import _UNSET, CHECK_FUNCS, _lookup
from src.gateway.log import CallLogEntry, summarize, write_jsonl
from src.gateway.record_state import state_from_record
from src.gateway.registry import CHECK_TABLE_PATH, REGISTRY, WRITE_ACTIONS, check_types

ROOT = Path(__file__).resolve().parents[2]
MAX_CALLS_SELECTIVE = 4    # R9.4; the monitor loop keeps to it, the gateway only guards against a caller bug
_DEFAULT = object()
CHECK_TABLE = yaml.safe_load(CHECK_TABLE_PATH.read_text(encoding="utf-8")) or {}
RESOURCE_KINDS = {k: set(v) for k, v in
                  (yaml.safe_load((ROOT / "configs" / "resource_kinds.yaml").read_text(encoding="utf-8")) or {}).items()}


class MissingFact(ValueError):
    """A record's key fact is not what the gateway answers from its hidden state (regenerate the record)."""

_KIND = {"path": "file or folder", "file": "file", "resource": "resource", "user": "user", "recipient": "recipient",
         "account": "account", "to_account": "account", "repo": "repository", "customer_id": "customer"}


class CallResult(BaseModel):
    status: Literal["ok", "error", "blocked_write"]
    tool: str
    args: dict
    facts: dict | None                  # only when ok
    error_code: Literal["unknown_tool", "invalid_args", "not_found", "write_not_allowed"] | None
    message: str | None                 # fixed templates only
    retry_available: bool               # the monitor may still retry after an error in this case

    def as_data(self, allowed: list[str]) -> dict:
        """What the monitor sees (R7.3, R7.4)."""
        if self.status == "ok":
            return dict(self.facts)
        out = {"error": self.error_code}
        if self.error_code == "unknown_tool":
            out["allowed"] = allowed
        elif self.error_code == "invalid_args":
            spec = REGISTRY[self.tool]
            out["expected"] = {p: d.get("type", "string") for p, d in spec.params.items()}
        if self.message:
            out["detail"] = self.message
        return out


def serialize(result: dict) -> str:
    """The text of a result as the prompt shows it (src/monitor/prompt_builder.render_results)."""
    return json.dumps(result, ensure_ascii=False)


def _schema_message(tool, args: dict) -> str:
    """One fixed-template message for the first schema problem."""
    for p in tool.required:
        if p not in args:
            return f"missing field '{p}'"
    for k in sorted(args):
        if k not in tool.params:
            return f"unexpected field '{k}'"
    for k in sorted(args):
        want = tool.params[k].get("type", "string")
        return f"field '{k}' must be a {want}" + (" of at least 1" if "minimum" in tool.params[k] else "")
    return "invalid arguments"


class Gateway:
    """One per case: counts, the retry flag and the log never leak between cases."""

    def __init__(self, state: CompanyState, case_id: str, setting: str = "selective", *, ood: bool = False,
                 action: dict | None = None, run_id: str = "", max_calls=_DEFAULT):
        self.state, self.case_id, self.setting, self.run_id = state, case_id, setting, run_id
        self.action = action or {}
        self.allowed = sorted(t for t, spec in REGISTRY.items() if ood or not spec.ood)
        if max_calls is _DEFAULT:
            max_calls = MAX_CALLS_SELECTIVE if setting == "selective" else None
        self.max_calls = max_calls
        self.log: list[CallLogEntry] = []
        self._retry_available = True

    # --- public ---------------------------------------------------------------------------------------
    def call(self, tool: str, args: dict) -> dict:
        """Run one call; the result as the monitor sees it, errors as data."""
        return self.call_result(tool, args).as_data(self.allowed)

    def call_result(self, tool: str, args: dict) -> CallResult:
        if self.max_calls is not None and len(self.log) >= self.max_calls:
            raise RuntimeError(f"{self.case_id}: more than {self.max_calls} gateway calls in {self.setting} (R9.4)")
        args = dict(args or {})
        res = self._run(tool, args)
        self._record(res)
        return res

    def summary(self) -> dict:
        return summarize(self.log)

    def write_log(self, path: str | Path) -> None:
        write_jsonl(self.log, path)

    # --- steps ----------------------------------------------------------------------------------------
    def _error(self, tool, args, code, message=None) -> CallResult:
        retry = self._retry_available
        self._retry_available = False
        return CallResult(status="error", tool=tool, args=args, facts=None, error_code=code, message=message,
                          retry_available=retry)

    def _run(self, tool: str, args: dict) -> CallResult:
        if tool in WRITE_ACTIONS:
            return CallResult(status="blocked_write", tool=tool, args=args, facts=None,
                              error_code="write_not_allowed", message=None, retry_available=self._retry_available)
        if tool not in self.allowed:
            return self._error(tool, args, "unknown_tool", f"unknown tool '{tool}'")
        spec = REGISTRY[tool]
        if any(True for _ in Draft202012Validator(spec.schema).iter_errors(args)):
            return self._error(tool, args, "invalid_args", _schema_message(spec, args))
        try:
            facts = CHECK_FUNCS[tool](self.state, **args)
        except Ambiguous:
            return self._error(tool, args, "invalid_args",
                               f"more than one file named '{args[spec.resource_param]}', give the full path")
        except NotFound:
            ref = args[spec.resource_param]
            return self._error(tool, args, "not_found", f"no {_KIND.get(spec.resource_param, 'resource')} named '{ref}'")
        check_types(spec, facts)
        return CallResult(status="ok", tool=tool, args=args, facts=facts, error_code=None, message=None,
                          retry_available=self._retry_available)

    def _matches_action(self, tool: str, args: dict) -> bool | None:
        spec = REGISTRY.get(tool)
        if spec is None or spec.resource_param not in args or not self.action:
            return None
        ref = str(args[spec.resource_param])
        names = {str(v) for v in self.action.get("args", {}).values() if isinstance(v, (str, int))}
        names |= {n.rstrip("/").rsplit("/", 1)[-1] for n in names}
        return ref in names or ref.rstrip("/").rsplit("/", 1)[-1] in names

    def _record(self, res: CallResult) -> None:
        prev = self.log[-1] if self.log else None
        self.log.append(CallLogEntry(
            run_id=self.run_id, case_id=self.case_id, setting=self.setting, call_index=len(self.log) + 1,
            tool=res.tool, args=res.args, status=res.status, error_code=res.error_code, facts=res.facts,
            is_retry=prev is not None and prev.status == "error",
            resource_matches_action=self._matches_action(res.tool, res.args), noisy=False))


# ---------- builders ----------------------------------------------------------------------------------

_REQUESTERS: dict[str, str] = {}


def _requested_by(seed_id: str, set_name: str) -> str:
    """The acting user of the scenario (seed `requested_by`; the record does not carry it). Not gold."""
    if seed_id not in _REQUESTERS:
        sub = "ood" if set_name == "ood" else "in_domain"
        path = ROOT / "data" / "seeds" / sub / f"{seed_id}.yaml"
        seed = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
        _REQUESTERS[seed_id] = seed.get("requested_by") or "current_user"
    return _REQUESTERS[seed_id]


def resource_kind(name) -> str | None:
    """The kind configs/resource_kinds.yaml gives a name (system, link), None for anything else."""
    return next((kind for kind, names in RESOURCE_KINDS.items() if str(name) in names), None)


def table_calls(action: dict, current_user: str) -> list[tuple[str, dict]]:
    """The calls configs/check_table.yaml lists for an action, args filled from the action (R7.5).
    A row is skipped when its if_arg is absent or an unless_kind argument names a resource of that kind,
    never because a resource is missing from the state."""
    out = []
    for e in CHECK_TABLE.get(action["name"]) or []:
        if "if_arg" in e and e["if_arg"] not in action["args"]:
            continue
        if any(resource_kind(action["args"].get(arg)) == kind for arg, kind in (e.get("unless_kind") or {}).items()):
            continue
        args = {k: current_user if v == "$current_user" else action["args"].get(v) for k, v in e["args"].items()}
        out.append((e["check"], {k: v for k, v in args.items() if v is not None}))
    return out


def _same(ref, res) -> bool:
    return str(ref) == str(res) or str(ref).rstrip("/").rsplit("/", 1)[-1] == str(res)


def verify_key_facts(record: dict, state: CompanyState, current_user: str) -> None:
    """Raise MissingFact if a table check on a key fact's resource does not answer that fact's value
    (e.g. the hidden state never states it, so the simulator default answers). Facts that disagree on
    purpose (two key facts on one resource and one field, T5) are skipped. Not logged, not counted."""
    key_facts = record["hidden"].get("key_facts") or {}
    if not key_facts:
        return
    scratch = Gateway(state, record["record_id"], "always", ood=record["set"] == "ood")
    for tool_name, args in table_calls(record["visible"]["proposed_action"], current_user):
        tool = REGISTRY[tool_name]
        out = None
        for key, value in key_facts.items():
            res, fact = key.rsplit(".", 1)
            if fact not in tool.facts or not _same(args.get(tool.resource_param), res):
                continue
            field, values = tool.facts[fact]["field"], tool.facts[fact]["values"]
            rivals = [k for k in key_facts if k != key and k.rsplit(".", 1)[0] == res
                      and tool.facts.get(k.rsplit(".", 1)[1], {}).get("field") == field]
            if rivals:
                continue
            want = value if values is None else _lookup(values, value)
            out = out if out is not None else scratch.call(tool_name, args)
            if want is _UNSET or "error" in out or out[field] != want:
                raise MissingFact(f"{record['record_id']}: hidden state does not give {key} = {value!r} "
                                  f"({tool_name}.{field} answers {out.get(field, out)!r})")


def for_record(record: dict, setting: str = "selective", run_id: str = "", max_calls=_DEFAULT,
               verify: bool = True) -> Gateway:
    """A gateway over the state stored in the record (training data and evaluation on our records).
    Reads record["hidden"], record["set"], the proposed action and the seed's requested_by; never
    record["gold"]. Raises MissingFact when the hidden state cannot answer one of its own key facts."""
    current = _requested_by(record["seed_id"], record["set"])
    state = state_from_record(record, current)
    if verify:
        verify_key_facts(record, state, current)
    return Gateway(state, record["record_id"], setting, ood=record["set"] == "ood",
                   action=record["visible"]["proposed_action"], run_id=run_id, max_calls=max_calls)


def call_check(state: CompanyState, tool: str, args: dict, ood: bool = True) -> dict:
    """One call on a simulator state, outside a case (the 2-person plan's interface): validates, blocks
    writes, runs. For counted calls build a Gateway per case."""
    return Gateway(state, "call_check", "selective", ood=ood).call(tool, args)
