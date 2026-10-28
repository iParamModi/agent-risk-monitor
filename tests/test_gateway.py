"""src/gateway: the check gateway (decisions.md R7.2-R7.6, R9.4). Numbers refer to the gateway spec's test list.

Runs on the simulator's seed state (lma_agent) and on every record (for_record), with the same check functions.
"""
import json
import re

import pytest
import yaml

from lma_agent.sim.seed_state import build_seed_state, state_hash
from src.common.io import REPO_ROOT, read_jsonl
from src.gateway.checks import CHECK_FUNCS, stated
from src.gateway.gateway import Gateway, call_check, for_record
from src.gateway.registry import REGISTRY, WRITE_ACTIONS, check_types

RECORDS = [r for name in ("all_in_domain", "all_ood") for r in read_jsonl(REPO_ROOT / "data" / "records" / f"{name}.jsonl")]
TABLE = yaml.safe_load((REPO_ROOT / "configs" / "check_table.yaml").read_text(encoding="utf-8"))

# One valid call per tool on the simulator's seed state.
SIM_ARGS = {
    "check_file_sharing": {"path": "/project/report_7.pdf"},
    "check_file_owner": {"file": "/project/report_7.pdf"},
    "check_file_classification": {"file": "/project/report_7.pdf"},
    "check_file_lock": {"file": "/project/report_7.pdf"},
    "check_file_pii": {"file": "/project/report_7.pdf"},
    "check_retention_status": {"resource": "C-1001"},
    "check_legal_hold": {"resource": "/project/report_7.pdf"},
    "check_owner_team": {"resource": "AcmePay"},
    "check_user_authorization": {"user": "u_arjun", "resource": "AcmePay"},
    "check_user_clearance": {"user": "u_dev"},
    "check_owner_approval": {"user": "u_dev", "resource": "AcmePay"},
    "check_admin_count": {"user": "u_arjun", "resource": "infra-config"},
    "check_recipient_type": {"recipient": "c_globex"},
    "check_recipient_nda": {"recipient": "c_globex"},
    "check_recipient_verification": {"recipient": "c_globex"},
    "check_recipient_region": {"recipient": "ACC-VENDOR-1"},
    "check_approval_limit": {"user": "u_riya"},
    "check_account_balance": {"account": "ACC-OPS"},
    "check_sanctions": {"account": "ACC-VENDOR-1"},
    "check_transfer_compliance": {"to_account": "ACC-VENDOR-1", "amount_inr": 75000},
    "check_repository_status": {"repo": "AcmePay"},
    "check_repository_activity": {"repo": "AcmePay"},
    "check_repository_archived": {"repo": "AcmePay"},
    "check_repository_backup": {"repo": "AcmePay"},
    "check_repository_compliance": {"repo": "AcmePay"},
    "check_customer_consent": {"customer_id": "C-1001"},
    "check_customer_flags": {"customer_id": "C-1001"},
}


def sim_gateway(setting="selective", **kw):
    return Gateway(build_seed_state(0), "sim-case", setting, ood=True, **kw)


def requested_by(record):
    from src.gateway.gateway import _requested_by
    return _requested_by(record["seed_id"], record["set"])


def table_calls(record):
    """The always-setting calls for a record's action (configs/check_table.yaml), args filled from the action."""
    action, out = record["visible"]["proposed_action"], []
    for e in TABLE.get(action["name"]) or []:
        if "if_arg" in e and e["if_arg"] not in action["args"]:
            continue
        args = {k: requested_by(record) if v == "$current_user" else action["args"].get(v) for k, v in e["args"].items()}
        out.append((e["check"], {k: v for k, v in args.items() if v is not None}))
    return out


# ---------- basic (1-5) ----------

def test_every_tool_has_a_function_and_a_sim_call():
    assert set(CHECK_FUNCS) == set(REGISTRY) == set(SIM_ARGS)


@pytest.mark.parametrize("tool", sorted(SIM_ARGS))
def test_1_valid_call_returns_typed_facts(tool):
    res = sim_gateway().call_result(tool, SIM_ARGS[tool])
    assert res.status == "ok" and res.error_code is None, res
    check_types(REGISTRY[tool], res.facts)
    assert list(res.facts) == list(REGISTRY[tool].returns)


def test_2_unknown_tool():
    out = sim_gateway().call("check_user_auth", {"user": "u_dev"})
    assert out["error"] == "unknown_tool" and "check_user_authorization" in out["allowed"]
    assert sim_gateway().call("get_file_info", {"file": "/project/report_7.pdf"})["error"] == "unknown_tool"


@pytest.mark.parametrize("args,detail", [
    ({}, "missing field 'file'"),
    ({"file": "/project/report_7.pdf", "extra": 1}, "unexpected field 'extra'"),
    ({"file": 7}, "field 'file' must be a string"),
])
def test_3_bad_args(args, detail):
    out = sim_gateway().call("check_file_lock", args)
    assert out["error"] == "invalid_args" and out["detail"] == detail and out["expected"] == {"file": "string"}


def test_3_bad_amount():
    out = sim_gateway().call("check_transfer_compliance", {"to_account": "ACC-OPS", "amount_inr": 0})
    assert out["error"] == "invalid_args"


@pytest.mark.parametrize("tool,args", [
    ("check_file_lock", {"file": "/nope/report_9.pdf"}),
    ("check_repository_status", {"repo": "no-such-repo"}),
    ("check_user_clearance", {"user": "u_nobody"}),
    ("check_account_balance", {"account": "ACC-NONE"}),
    ("check_customer_flags", {"customer_id": "C-9999"}),
])
def test_4_unknown_resource_says_nothing_else(tool, args):
    out = sim_gateway().call(tool, args)
    ref = next(iter(args.values()))
    assert out["error"] == "not_found" and set(out) == {"error", "detail"}
    assert re.fullmatch(rf"no [a-z ]+ named '{re.escape(ref)}'", out["detail"]), out


@pytest.mark.parametrize("action", sorted(WRITE_ACTIONS))
def test_5_writes_are_blocked_and_change_nothing(action):
    gw = sim_gateway()
    before = state_hash(gw.state)
    out = gw.call(action, {"file": "/project/report_7.pdf"})
    assert out == {"error": "write_not_allowed"}
    assert state_hash(gw.state) == before
    assert gw.log[-1].status == "blocked_write"


def test_5_checks_change_nothing():
    gw = sim_gateway(max_calls=None)
    before = state_hash(gw.state)
    for tool, args in SIM_ARGS.items():
        gw.call(tool, args)
    assert state_hash(gw.state) == before


# ---------- budgets and counting (6-10) ----------

def test_6_retry_and_recovery():
    gw = sim_gateway()
    first = gw.call_result("check_file_lock", {})
    second = gw.call_result("check_file_lock", {"file": "/project/report_7.pdf"})
    assert first.retry_available and second.status == "ok"
    assert gw.summary()["recovered"] and gw.log[1].is_retry
    gw2 = sim_gateway()
    gw2.call_result("check_file_lock", {})
    assert gw2.call_result("check_nothing", {}).retry_available is False


def test_7_blocked_write_does_not_use_the_retry():
    gw = sim_gateway()
    gw.call("delete_file", {"file": "/project/report_7.pdf"})
    assert gw.call_result("check_file_lock", {}).retry_available is True


def test_8_selective_cap_always_unlimited():
    gw = sim_gateway()
    for _ in range(4):                               # R9.4: 4 gateway calls in selective, errors included
        gw.call("check_file_lock", {"file": "/project/report_7.pdf"})
    with pytest.raises(RuntimeError):
        gw.call("check_file_lock", {"file": "/project/report_7.pdf"})
    gw = sim_gateway("always")
    for _ in range(10):
        gw.call("check_file_lock", {"file": "/project/report_7.pdf"})
    assert gw.summary()["valid_checks"] == 10


def test_9_cases_do_not_share_counts():
    a, b = sim_gateway(), sim_gateway()
    a.call("check_file_lock", {})
    assert b.log == [] and b.call_result("check_file_lock", {}).retry_available is True


def test_10_call_index_in_order_with_all_statuses():
    gw = sim_gateway()
    gw.call("check_nothing", {})
    gw.call("delete_file", {"file": "x"})
    gw.call("check_file_lock", {"file": "/project/report_7.pdf"})
    assert [(e.call_index, e.status) for e in gw.log] == [(1, "error"), (2, "blocked_write"), (3, "ok")]
    assert gw.summary()["tools"] == ["check_nothing", "delete_file", "check_file_lock"]


# ---------- records: safety, leakage, answers (11, 12) ----------

def test_11_every_table_call_on_every_record_is_typed_or_an_error():
    """check_types raises inside the gateway when a value breaks its declared type."""
    n = 0
    for r in RECORDS:
        if r["task"] != "decide_action":
            continue
        gw = for_record(r, setting="always")
        for tool, args in table_calls(r):
            gw.call(tool, args)
            n += 1
    assert n > 500


def test_gold_checks_return_the_records_key_facts():
    """For every record: each gold check on the resource of a key fact answers that fact's stated value,
    through the tool's facts map. This is what the second-pass training examples teach."""
    checked = 0
    for r in RECORDS:
        gw = for_record(r)
        for c in r["gold"]["required_checks"] or []:
            if None in c["args"].values():
                continue                          # OOD-CUST-T1-006: gold arg missing (seed requested_by)
            out = gw.call(c["tool"], c["args"])
            assert "error" not in out, (r["record_id"], c, out)
            tool = REGISTRY[c["tool"]]
            ref = c["args"][tool.resource_param]
            for key, value in r["hidden"]["key_facts"].items():
                res, fact = key.rsplit(".", 1)
                if fact not in tool.facts or res != ref:
                    continue
                target = tool.facts[fact]
                rivals = [k for k in r["hidden"]["key_facts"] if k != key and k.rsplit(".", 1)[0] == res
                          and tool.facts.get(k.rsplit(".", 1)[1], {}).get("field") == target["field"]]
                if rivals:                        # T5 facts_disagree: the two facts disagree on purpose
                    continue
                want = value
                if target["values"] is not None:
                    from src.gateway.checks import _lookup
                    want = _lookup(target["values"], value)
                assert out[target["field"]] == want, (r["record_id"], c, key, value, out)
                checked += 1
    assert checked > 250


def test_12_errors_never_carry_hidden_values_or_policy_text():
    for r in RECORDS[:200]:
        gw = for_record(r, max_calls=None)
        hidden = {str(v) for v in r["hidden"]["key_facts"].values() if isinstance(v, str) and len(str(v)) > 3}
        outs = [gw.call("check_nothing", {}), gw.call("check_file_lock", {"file": "zz_missing.pdf"}),
                gw.call("check_file_lock", {"path": 1}), gw.call("delete_file", {"file": "x"})]
        text = json.dumps(outs)
        assert not re.search(r"P_[A-Z]+_\d+", text)
        assert not [h for h in hidden if h in text and h not in json.dumps(sorted(REGISTRY))], (r["record_id"], text)


def test_for_record_never_reads_gold():
    r = dict(next(r for r in RECORDS if r["gold"]["check_needed"]), gold=None)
    assert "error" in for_record(r).call("check_nothing", {})


def test_ood_tools_only_on_ood_records():
    ind = for_record(next(r for r in RECORDS if r["set"] == "in_domain"))
    ood = for_record(next(r for r in RECORDS if r["set"] == "ood" and r["hidden"]["state"].get("customer_records")))
    cid = ood.state.customers and next(iter(ood.state.customers))
    assert ind.call("check_customer_flags", {"customer_id": "C-1"})["error"] == "unknown_tool"
    assert "error" not in ood.call("check_customer_flags", {"customer_id": cid})


# ---------- determinism (15), log ----------

def test_15_same_case_twice_same_log():
    r = next(r for r in RECORDS if r["gold"]["required_checks"])
    logs = []
    for run_id in ("a", "b"):
        gw = for_record(r, run_id=run_id)
        for c in r["gold"]["required_checks"]:
            gw.call(c["tool"], c["args"])
        logs.append([e.model_dump(exclude={"run_id"}) for e in gw.log])
    assert logs[0] == logs[1]


def test_log_flags_a_call_on_another_resource(tmp_path):
    r = next(r for r in RECORDS if r["visible"]["proposed_action"]["name"] == "delete_file")
    gw = for_record(r, setting="selective")
    target = r["visible"]["proposed_action"]["args"]["file"]
    gw.call("check_file_lock", {"file": target})
    gw.call("check_file_lock", {"file": "some_other_file.pdf"})
    assert [e.resource_matches_action for e in gw.log] == [True, True if target == "some_other_file.pdf" else False]
    gw.write_log(tmp_path / "gateway_log.jsonl")
    rows = [json.loads(line) for line in (tmp_path / "gateway_log.jsonl").read_text().splitlines()]
    assert len(rows) == 2 and rows[0]["case_id"] == r["record_id"]


def test_call_check_wrapper():
    state = build_seed_state(0)
    assert call_check(state, "check_file_lock", {"file": "/project/report_7.pdf"})["locked"] is False
    assert call_check(state, "move_file", {}) == {"error": "write_not_allowed"}


def test_stated_fact_without_a_value_map_entry_raises():
    from src.gateway.checks import UnmappedFact
    gw = sim_gateway()
    gw.state.files["/project/report_7.pdf"].attrs = {"sensitivity": "top_secret"}
    with pytest.raises(UnmappedFact):
        gw.call("check_file_classification", {"file": "/project/report_7.pdf"})
    assert stated(gw.state.files["/project/report_8.pdf"], "check_file_lock", "locked") is not None
