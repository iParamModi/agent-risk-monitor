from datetime import date

import pytest
from pydantic import ValidationError

from lma_agent.sim.models import (
    AssistantMsg, CompanyState, EpisodeResult, GateDecision, StepLog, Task, ToolCall,
)

SAMPLE_STATE = {
    "current_user": "u_riya",
    "files": {"/a.txt": {"path": "/a.txt", "owner": "u_riya", "sharing": "none",
                         "classification": "internal", "modified": "2024-03-02"}},
    "users": {"u_riya": {"user_id": "u_riya", "name": "Riya", "email": "riya@acme.com",
                         "team": "Finance", "job_role": "Manager", "approval_limit": 500000}},
    "contacts": {"x@acme.com": {"email": "x@acme.com", "name": "X", "org": "Acme", "is_internal": True}},
    "permissions": {"AcmePay": {"u_riya": "viewer"}},
    "accounts": {"ACC-OPS": {"account_id": "ACC-OPS", "owner": "u_riya", "balance": 10}},
    "repos": {"r": {"name": "r", "owner": "u_riya", "description": "", "visibility": "private",
                    "production": True, "active": True}},
    "inbox": [{"email_id": "e1", "sender": "a@acme.com", "to": ["riya@acme.com"],
               "subject": "hi", "body": "hello"}],
    "customers": {"C-1": {"customer_id": "C-1", "name": "C", "email": "c@x.com",
                          "status": "active", "data": {}}},
}


def test_company_state_builds_from_dict():
    state = CompanyState.model_validate(SAMPLE_STATE)
    assert state.files["/a.txt"].modified == date(2024, 3, 2)
    assert state.files["/a.txt"].shared_with == []
    assert state.sent == [] and state.exports == []


def test_bad_literal_is_rejected():
    bad = {**SAMPLE_STATE, "files": {"/a.txt": {**SAMPLE_STATE["files"]["/a.txt"], "sharing": "world"}}}
    with pytest.raises(ValidationError):
        CompanyState.model_validate(bad)


def test_message_and_log_classes_build():
    call = ToolCall(id="c1", name="read_file", args={"path": "/a.txt"})
    msg = AssistantMsg(content=None, tool_calls=[call], raw={"role": "assistant"})
    gate = GateDecision(decision="BLOCK", policy_id="P1", reason="no")
    log = StepLog(episode_id="e", step=1, trajectory_so_far=[], proposed_action=call,
                  tool_type="read", gate_decision=None, state_hash_before="h", executed=True, result={})
    task = Task(task_id="t", domain="FILE", prompt="do it")
    ep = EpisodeResult(episode_id="e", task_id="t", status="done", final_answer="ok", messages=[],
                       steps=[log], n_llm_calls=1, n_tool_errors=0, final_state_hash="h")
    assert msg.tool_calls[0].name == "read_file"
    assert gate.decision == "BLOCK"
    assert task.user_confirms is True and task.overrides == {}
    assert ep.steps[0].gold_decision is None
