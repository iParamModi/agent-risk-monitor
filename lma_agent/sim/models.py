"""Pydantic data classes: company state, messages, gate decisions, logs and tasks."""
from datetime import date
from typing import Literal

from pydantic import BaseModel


class File(BaseModel):
    path: str
    owner: str
    sharing: Literal["none", "internal", "external"]
    shared_with: list[str] = []
    classification: Literal["public", "internal", "confidential"]  # hidden from the agent
    modified: date
    content: str | dict = ""


class User(BaseModel):
    user_id: str
    name: str
    email: str
    team: str
    job_role: str
    approval_limit: int  # hidden from the agent


class Contact(BaseModel):
    email: str
    name: str
    org: str
    is_internal: bool  # hidden from the agent


class Account(BaseModel):
    account_id: str
    owner: str
    balance: int


class Repo(BaseModel):
    name: str
    owner: str
    description: str
    visibility: Literal["public", "private"]
    production: bool  # hidden from the agent
    active: bool


class Email(BaseModel):
    email_id: str
    sender: str
    to: list[str]
    subject: str
    body: str
    attachments: list[str] = []


class Customer(BaseModel):
    customer_id: str
    name: str
    email: str
    status: Literal["active", "archived"]
    data: dict


class CompanyState(BaseModel):
    current_user: str
    files: dict[str, File]
    users: dict[str, User]
    contacts: dict[str, Contact]
    permissions: dict[str, dict[str, str]]
    accounts: dict[str, Account]
    repos: dict[str, Repo]
    inbox: list[Email]
    sent: list[Email] = []
    customers: dict[str, Customer] = {}
    exports: list[dict] = []


class ToolCall(BaseModel):
    id: str
    name: str
    args: dict


class AssistantMsg(BaseModel):
    content: str | None
    tool_calls: list[ToolCall]
    raw: dict


class GateDecision(BaseModel):
    decision: Literal["ALLOW", "ASK_CONFIRMATION", "BLOCK", "ESCALATE"]
    policy_id: str | None = None
    reason: str = ""


class StepLog(BaseModel):
    episode_id: str
    step: int
    trajectory_so_far: list[dict]
    proposed_action: ToolCall
    tool_type: Literal["read", "write", "invalid"]
    gate_decision: str | None
    gold_decision: str | None = None
    state_hash_before: str
    executed: bool
    result: dict


class Task(BaseModel):
    task_id: str
    domain: str
    prompt: str
    state_seed: int = 0
    overrides: dict = {}
    user_confirms: bool = True
    expected_tools: list[str] = []


class EpisodeResult(BaseModel):
    episode_id: str
    task_id: str
    status: Literal["done", "escalated", "max_steps", "error"]
    final_answer: str | None
    messages: list[dict]
    steps: list[StepLog]
    n_llm_calls: int
    n_tool_errors: int
    final_state_hash: str
