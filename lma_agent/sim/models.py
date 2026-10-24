"""Pydantic data classes: company state, messages, gate decisions, logs and tasks."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, StringConstraints
from typing_extensions import Annotated

Sharing = Annotated[str, StringConstraints(pattern=r"^(internal|public|external:[\w.\-]+)$")]
Level = Literal["read", "write", "admin"]


class Folder(BaseModel):
    path: str
    sharing: Sharing  # files inside inherit this unless they have their own
    owner: str | None = None
    attrs: dict = {}  # hidden facts, e.g. {"legal_hold": True}


class File(BaseModel):
    path: str
    owner: str
    sharing: Sharing | None = None  # None = inherit the folder's sharing
    shared_with: list[str] = []
    classification: Literal["public", "internal", "confidential", "restricted"]  # hidden from the agent
    modified: date
    content: str | dict = ""
    attrs: dict = {}  # hidden facts, e.g. {"locked": True, "legal_hold": True}

    @property
    def name(self) -> str:
        return self.path.rsplit("/", 1)[-1]

    @property
    def folder(self) -> str:
        return self.path.rsplit("/", 1)[0] or "/"


class User(BaseModel):
    user_id: str
    name: str
    email: str
    team: str
    role: str
    approval_limit_inr: int  # hidden from the agent
    is_external: bool = False  # hidden from the agent
    status: Literal["active", "terminated"] = "active"
    attrs: dict = {}  # hidden facts, e.g. {"authorized_financial": True}


class Contact(BaseModel):
    contact_id: str
    email: str
    name: str
    org: str
    kind: Literal["internal", "external", "public"]  # hidden from the agent
    attrs: dict = {}  # hidden facts, e.g. {"nda_in_place": False}


class Account(BaseModel):
    account_id: str
    owner: str
    type: Literal["company", "internal", "personal", "vendor"]  # hidden from the agent
    balance_inr: int
    attrs: dict = {}  # hidden facts, e.g. {"sanctioned": True, "kyc_status": "pending"}


class Repo(BaseModel):
    name: str
    owner: str
    owner_team: str
    description: str
    visibility: Literal["public", "private"]
    production: bool  # hidden from the agent
    archived: bool = False
    attrs: dict = {}  # hidden facts, e.g. {"has_active_deploys": True}


class Event(BaseModel):
    event_id: str
    title: str
    organizer: str
    attendees: list[str]


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
    attrs: dict = {}  # hidden facts, e.g. {"consent": "given", "legal_hold": False}


class CompanyState(BaseModel):
    current_user: str
    folders: dict[str, Folder] = {}
    files: dict[str, File]
    users: dict[str, User]
    contacts: dict[str, Contact]
    permissions: dict[str, dict[str, Level]]
    accounts: dict[str, Account]
    repos: dict[str, Repo]
    inbox: list[Email]
    sent: list[Email] = []
    customers: dict[str, Customer] = {}
    exports: list[dict] = []
    events: list[Event] = []


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
