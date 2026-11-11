"""run_monitor(record, setting, model): one case through the monitor (PLAN Step 14, decisions.md R9).

Returns one predictions.jsonl row in the format of docs/evaluation_metrics.md section 2.

The loop never hands the record to the prompt builder: prompts get `record["visible"]`, the retrieved
policies, the check-tool list and gateway results only. `gold` is read for two things: the oracle
check list (whose facts reach the prompt as gateway results, like any check) and the copy into the row.
Policies are shown under local numbers in a fixed random order per record (number_policies); the cited
numbers in a DECISION are mapped back to policy ids before the row is written.
"""
import time

from src.monitor.parser import parse_output
from src.monitor.prompt_builder import (as_messages, build_decide_prompt, build_risk_prompt, number_policies,
                                        refs_to_ids)
from src.monitor.settings import DECIDE_NOW, MAX_GATEWAY_CALLS, MAX_PASSES, SETTINGS, checks_before_pass

ERROR_NAMES = ("unknown_tool", "invalid_args", "not_found", "write_not_allowed")   # R7.3, R7.4
COPIED_FIELDS = ("record_id", "seed_id", "domain", "case_type", "subtype", "pair_side", "task")


class _Case:
    """Running totals for one case: passes, tokens, gateway calls and check results."""

    def __init__(self, model, gateway):
        self.model, self.gateway = model, gateway
        self.passes = 0
        self.tokens_in: int | None = 0
        self.tokens_out: int | None = 0
        self.calls: list[dict] = []      # for predictions.jsonl
        self.results: list[dict] = []    # for the prompt

    def ask(self, messages: list[dict], allowed: tuple[str, ...]) -> tuple[dict | None, str]:
        gen = self.model.generate(messages)
        self.passes += 1
        self.tokens_in = None if self.tokens_in is None or gen.tokens_in is None else self.tokens_in + gen.tokens_in
        self.tokens_out = None if self.tokens_out is None or gen.tokens_out is None else self.tokens_out + gen.tokens_out
        return parse_output(gen.text, allowed), gen.text

    def check(self, checks: list[dict], added_by: str | None = None) -> bool:
        """Send checks to the gateway; True if any of them failed. Every call is counted (R7.6). added_by marks
        calls the loop added itself (v2 second-source rule), so reports can count them apart."""
        if self.gateway is None:
            raise RuntimeError("this setting needs a gateway, none was given")
        failed = False
        for c in checks:
            result = self.gateway.call(c["tool"], c["args"])
            error = result.get("error") if isinstance(result, dict) else None
            error = error if error in ERROR_NAMES else None
            failed = failed or error is not None
            call = {"tool": c["tool"], "args": c["args"], "error": error}
            if added_by:
                call["added_by"] = added_by
            self.calls.append(call)
            self.results.append({"tool": c["tool"], "args": c["args"], "result": result})
        return failed


def _norm(value) -> str:
    return str(value).strip().lower()


def second_source_calls(request: dict, table_checks: list[dict], siblings: dict) -> list[dict]:
    """v2 rule: when the model's missing_fact ("<attribute> of <resource>") is a fact that two or more check tools
    report (configs/fact_checks.yaml: account_type, modifiable, role_eligible), the checks of the other tools on
    that resource, taken from this action's always table, so the monitor sees both sources.
    siblings: attribute -> [(tool, resource param)] for those facts only."""
    attribute, _, resource = (request.get("missing_fact") or "").partition(" of ")
    asked = {(c["tool"], _norm(c.get("args"))) for c in request.get("checks") or []}
    out = []
    for tool, param in siblings.get(attribute.strip(), ()):
        for t in table_checks:
            key = (t["tool"], _norm(t["args"]))
            if t["tool"] == tool and _norm(t["args"].get(param)) == _norm(resource) and key not in asked:
                asked.add(key)
                out.append({"tool": t["tool"], "args": dict(t["args"])})
    return out


def _selective(case: _Case, visible, policies, check_tools, table_checks=(), siblings=None,
               hints: bool = False, second_ask: bool = False) -> dict | None:
    may_check, retry_used = True, False
    while case.passes < MAX_PASSES:
        prompt = build_decide_prompt(visible, policies, check_tools, may_check=may_check, results=case.results,
                                     hints=hints)
        obj, _ = case.ask(as_messages(prompt), ("DECISION", "NEED_INFORMATION") if may_check else ("DECISION",))
        if obj is None or obj["type"] == "DECISION":
            return obj
        budget = MAX_GATEWAY_CALLS - len(case.calls)
        failed = case.check(obj["checks"][:budget])
        if siblings:
            extra = second_source_calls(obj, list(table_checks or ()), siblings)
            budget = MAX_GATEWAY_CALLS - len(case.calls)
            if extra and budget > 0:
                failed = case.check(extra[:budget], added_by="second_source") or failed
        # One retry after a tool error (R9.4): the next pass may ask again, then the last pass must decide.
        # second_ask (v3 candidate): the same one extra ask also without an error, while passes and calls remain.
        room = case.passes + 2 <= MAX_PASSES and len(case.calls) < MAX_GATEWAY_CALLS
        may_check = (failed or second_ask) and not retry_used and room
        retry_used = retry_used or may_check
    return None


def _never(case: _Case, visible, policies, check_tools) -> dict | None:
    messages = as_messages(build_decide_prompt(visible, policies, check_tools, may_check=False, no_checks=True))
    obj, text = case.ask(messages, ("DECISION", "NEED_INFORMATION"))
    if obj is None or obj["type"] == "DECISION":
        return obj
    # The model asked anyway: re-prompt once, count the pass (PLAN 2.7).
    messages += [{"role": "assistant", "content": text}, {"role": "user", "content": DECIDE_NOW}]
    obj, _ = case.ask(messages, ("DECISION",))
    return obj


def run_monitor(record: dict, setting: str, model, gateway=None, policies: list[dict] = (),
                check_tools: list[dict] = (), check_table: dict | None = None,
                table_checks: list[dict] | None = None, siblings: dict | None = None,
                hints: bool = False, second_ask: bool = False) -> dict:
    """One record, one setting.

    model:       has generate(messages) -> Generation (src/monitor/models.py)
    gateway:     has call(tool, args) -> dict, errors as data (src/gateway, R7.3); built for this record
    policies:    the top 3 retrieved policies [{"policy_id", "text"}] (Step 6); the prompt shows them by number
    check_tools: the check-tool list shown to the model (configs/tools.yaml, R7.1)
    check_table: action -> checks for the always setting (configs/check_table.yaml, R7.5)
    table_checks: the always checks of this record, already filled ([{"tool", "args"}], e.g. from
                 src.gateway.gateway.table_calls, which also fills $current_user); used instead of check_table
    siblings:    v2, selective only: the second-source map (second_source_calls); None = off (v1)
    hints:       v2, selective only: the two-sources line and the retry hint in the prompt; False = v1 prompt
    second_ask:  v3 candidate, selective only: one more NEED_INFORMATION after the first results, error or not
    """
    if setting not in SETTINGS:
        raise ValueError(f"unknown setting {setting!r}, expected one of {SETTINGS}")
    start = time.perf_counter()
    case = _Case(model, gateway)
    visible = record["visible"]
    policies, check_tools = number_policies(policies, record["record_id"]), list(check_tools)

    if record["task"] == "judge_trajectory":
        # External records: one pass, RISK format, no checks, in every setting (Step 14.3).
        output, _ = case.ask(as_messages(build_risk_prompt(visible)), ("RISK",))
    elif setting == "selective":
        output = _selective(case, visible, policies, check_tools, table_checks, siblings, hints, second_ask)
    elif setting == "never":
        output = _never(case, visible, policies, check_tools)
    else:   # always, oracle: fixed checks first, then one pass
        if setting == "always" and table_checks is not None:
            before = [{"tool": c["tool"], "args": dict(c["args"])} for c in table_checks]
        else:
            before = checks_before_pass(setting, visible["proposed_action"], check_table or {}, record["gold"])
        case.check(before)
        prompt = build_decide_prompt(visible, policies, check_tools, may_check=False, results=case.results)
        output, _ = case.ask(as_messages(prompt), ("DECISION",))
    output = refs_to_ids(output, policies)

    row = {k: record[k] for k in COPIED_FIELDS}
    row.update(gold=record["gold"], output=output, calls=case.calls, passes=case.passes,
               tokens_in=case.tokens_in, tokens_out=case.tokens_out,
               time_s=round(time.perf_counter() - start, 3))
    return row
