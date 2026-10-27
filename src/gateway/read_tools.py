"""check_* tools: read-only, return hidden facts to the monitor, never change the state.

Only the checks whose facts the simulator has typed fields for are implemented so far; the rest of
configs/check_tools.yaml comes with the gateway (PLAN Step 4) and returns {"error": "not_implemented"}.
"""
from pathlib import Path

import yaml

from lma_agent.sim import readers
from lma_agent.sim.models import CompanyState, ToolCall
from lma_agent.sim.readers import Ambiguous, NotFound
from lma_agent.tools.validate import validate_call

CHECK_SPECS = yaml.safe_load(open(Path(__file__).resolve().parents[2] / "configs" / "check_tools.yaml"))


def check_file_classification(state: CompanyState, file: str) -> dict:
    """Sensitivity label and DLP scan result of a file."""
    f = readers._get_file(state, file)
    return {"file": f.path, "classification": f.classification, "dlp_scan": f.dlp_scan}


def check_repository_status(state: CompanyState, repo: str) -> dict:
    """Production flag and lifecycle of a repository."""
    r = readers._get_repo(state, repo)
    return {"repo": r.name, "production": r.production, "lifecycle": r.lifecycle}


def check_repository_activity(state: CompanyState, repo: str) -> dict:
    """Running deploys, open incidents and dependants of a repository."""
    r = readers._get_repo(state, repo)
    return {"repo": r.name, "has_active_deploys": r.has_active_deploys,
            "has_active_incidents": r.has_active_incidents, "has_open_dependencies": r.has_open_dependencies}


def check_transfer_compliance(state: CompanyState, to_account: str, amount_inr: int) -> dict:
    """KYC, pre-approval, dual approval and duplicate flag of a payment to this payee."""
    a = readers._get_account(state, to_account)
    return {"to_account": a.account_id, "amount_inr": amount_inr, "kyc_status": a.kyc_status,
            "payee_preapproved": a.payee_preapproved, "dual_approval_obtained": a.dual_approval_obtained,
            "duplicate_flag": a.duplicate_flag}


def check_customer_flags(state: CompanyState, customer_id: str) -> dict:
    """Do-not-contact flag, dispute state and account status of a customer (OOD)."""
    if customer_id not in state.customers:
        raise NotFound(f"customer not found: {customer_id}")
    c = state.customers[customer_id]
    return {"customer_id": c.customer_id, "dnc": c.dnc, "dispute": c.dispute, "account_status": c.status}


CHECK_FUNCS = {f.__name__: f for f in [
    check_file_classification, check_repository_status, check_repository_activity,
    check_transfer_compliance, check_customer_flags,
]}


def run_check(state: CompanyState, call: ToolCall) -> dict:
    """Validate and run one check. Errors come back as {"error": ..., "detail": ...}, never raised."""
    problem = validate_call(call, CHECK_SPECS)
    if problem:  # same error names as tests/test_gateway_contract.py
        return {"error": "invalid_args" if problem["error"] == "bad_args" else problem["error"], "detail": problem["detail"]}
    if call.name not in CHECK_FUNCS:
        return {"error": "not_implemented", "detail": f"'{call.name}' has no gateway function yet"}
    try:
        return CHECK_FUNCS[call.name](state, **call.args)
    except NotFound as e:
        return {"error": "not_found", "detail": str(e)}
    except Ambiguous as e:
        return {"error": "ambiguous", "detail": str(e)}
