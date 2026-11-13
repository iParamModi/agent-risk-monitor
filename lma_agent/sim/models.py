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
    # Hidden from the agent, read by the check tools. Defaults trigger no policy.
    dlp_scan: Literal["clean", "flagged"] = "clean"
    locked: bool = False
    contains_pii: bool = False
    legal_hold: bool = False
    retention_hold: bool = False
    retain_until: str | None = None
    owner_team: str | None = None  # None = the owner's team
    attrs: dict = {}  # other hidden facts

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
    # Hidden from the agent. account_type is read by check_user_authorization; check_recipient_type reads
    # is_external, so the two can disagree only on purpose (T5 facts_disagree). Defaults trigger no policy.
    account_type: Literal["employee", "external_contractor", "external_vendor"] = "employee"
    authorized_hr: bool = True
    authorized_financial: bool = True
    authorized_pii: bool = True
    authorized_legal: bool = True
    clearance: Literal["junior", "senior"] = "senior"
    attrs: dict = {}  # other hidden facts


class Contact(BaseModel):
    contact_id: str
    email: str
    name: str
    org: str
    kind: Literal["internal", "external", "public"]  # hidden from the agent
    # Hidden from the agent. Defaults trigger no policy.
    nda_in_place: bool = True
    address_verified: bool = True
    region: str = "IN"
    domestic: bool = True
    attrs: dict = {}  # other hidden facts


class Account(BaseModel):
    account_id: str
    owner: str
    type: Literal["company", "internal", "personal", "vendor"]  # hidden from the agent
    balance_inr: int
    # Hidden from the agent: compliance of a payment to this account as payee. Defaults trigger no policy.
    kyc_status: Literal["complete", "pending"] = "complete"
    payee_preapproved: bool = True
    dual_approval_obtained: bool = True
    duplicate_flag: bool = False
    sanctioned: bool = False
    region: str = "IN"
    domestic: bool = True
    attrs: dict = {}  # other hidden facts


class Repo(BaseModel):
    name: str
    owner: str
    owner_team: str
    description: str
    visibility: Literal["public", "private"]
    production: bool  # hidden from the agent
    archived: bool = False
    # Hidden from the agent. Defaults trigger no policy; lifecycle None = not recorded.
    lifecycle: Literal["active", "end_of_life"] | None = None
    has_active_deploys: bool = False
    has_active_incidents: bool = False
    has_open_dependencies: bool = False
    backup_exists: bool = True
    compliance_locked: bool = False
    modifiable: bool = True  # read by check_repository_compliance
    status_modifiable: bool = True  # read by check_repository_status; differs only in T5 facts_disagree
    attrs: dict = {}  # other hidden facts


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
    dnc: bool = False  # hidden from the agent: on the do-not-contact list
    dispute: Literal["none", "open", "closed"] = "none"  # hidden from the agent
    # Hidden from the agent. Defaults trigger no policy.
    export_consent: bool = True
    consent_scope: Literal["full", "support_only"] = "full"
    legal_hold: bool = False
    retention_hold: bool = False
    retain_until: str | None = None
    attrs: dict = {}  # other hidden facts


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
    transactions: list[dict] = []  # money moves logged by transfer_money / pay_bill, read by list_transactions
    messages: list[dict] = []  # chat messages logged by send_message
    # resource -> user -> owner approved this user's access (hidden). A missing entry counts as approved.
    owner_approvals: dict[str, dict[str, bool]] = {}


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
    list_shows_sharing: bool = False  # list_files also shows each file's sharing (demo tasks)
    expected: dict = {}  # demo tasks: what we expect to see (decision, checks); for the results table only
    title: str = ""  # demo tasks: short name for the website's task chips
    description: str = ""  # demo tasks: what the run shows, for the human viewer (never sent to the agent)


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
