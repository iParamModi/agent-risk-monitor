"""The company state the website shows: snapshot + state_diffs rebuild the simulator's REAL state at every step, and
the facts hidden from the monitor are marked from the gateway's own config (configs/check_tools.yaml)."""
import pytest

from lma_agent.agent.gate import allow_all
from lma_agent.agent.llm import FakeLLM, assistant_msg
from lma_agent.agent.loop import run_agent
from lma_agent.agent.user_sim import ScriptedUser
from lma_agent.sim.models import CompanyState, ToolCall
from lma_agent.sim.seed_state import apply_overrides, build_seed_state
from lma_agent.tasks.load_tasks import load_tasks
from lma_agent.tools.write_tools import apply_action
from src.live import events as ev
from src.live.company import apply_diff, company_snapshot, hidden_fields, state_at
from src.live.events import ListSink
from src.live.fake_monitor import RuleFakeMonitor
from src.live.monitor_gate import KeywordOnlyEmbedder
from src.live.scripted_agent import scripted_agent

TASKS = {t.task_id: t for t in load_tasks("lma_agent/tasks/demo_tasks.yaml")}

# Many kinds of change: a file deleted, money moved, a permission granted and revoked, a repo deleted, mail sent,
# a file moved and shared, a new row appended to a list.
WRITES = [
    ("delete_file", {"file": "/project/report_7.pdf"}),
    ("transfer_money", {"from_account": "ACC-OPS", "to_account": "ACC-VENDOR-1", "amount_inr": 25000}),
    ("grant_permission", {"user": "u_dev", "resource": "AcmePay", "level": "admin"}),
    ("revoke_permission", {"user": "u_dev", "resource": "AcmePay", "level": "admin"}),
    ("delete_repository", {"repo": "old-prototype"}),
    ("send_email", {"to": "c_globex", "subject": "Q3", "body": "See attached.",
                    "attachment": "/finance/q3_budget.xlsx"}),
    ("move_file", {"file": "/project/report_8.pdf", "to": "/Public"}),
    ("share_file", {"file": "/project/roadmap_2026.docx", "with": "external_link"}),
    ("delete_file", {"file": "/does/not/exist.pdf"}),                     # an error: state unchanged
]


def as_state(d: dict) -> CompanyState:
    return CompanyState.model_validate(d)


def test_hidden_fields_come_from_the_gateway_config():
    h = hidden_fields()
    assert h["files"]["sharing"] == {"checks": ["check_file_sharing"], "revealed_by": ["get_file_info"]}
    assert h["repos"]["production"] == {"checks": ["check_repository_status"], "revealed_by": []}
    assert "check_approval_limit" in h["users"]["approval_limit_inr"]["checks"]
    assert "classification" in h["files"] and "legal_hold" in h["customers"] and "sanctioned" in h["accounts"]
    assert "attrs" in h["files"] and h["owner_approvals"]["*"]["checks"] == ["check_owner_approval"]
    for coll, names in (("files", ("path", "modified", "content")), ("repos", ("name", "description")),
                        ("users", ("user_id", "name", "email"))):
        assert not set(names) & set(h[coll]), f"{coll}: identifiers or visible fields marked hidden"


def test_every_write_rebuilds_the_real_state():
    state = build_seed_state(0)
    rebuilt = company_snapshot(TASKS["demo_hidden"], state)["state"]
    applied = 0
    for i, (name, args) in enumerate(WRITES):
        new, result = apply_action(state, ToolCall(id=f"w{i}", name=name, args=args))
        applied += "error" not in result
        rebuilt = apply_diff(rebuilt, ev.state_diff(state, new))
        assert rebuilt == new.model_dump(mode="json"), f"after {name}"
        assert as_state(rebuilt) == new
        state = new
    assert applied >= 7, "most writes should apply, or the test proves little"


def _run(task_id, confirms, setting, monkeypatch):
    real_after = []
    real_diff = ev.state_diff

    def spy(before, after):
        real_after.append(after.model_dump(mode="json"))
        return real_diff(before, after)
    monkeypatch.setattr(ev, "state_diff", spy)
    task = TASKS[task_id]
    state = apply_overrides(build_seed_state(task.state_seed), task.overrides)
    from lma_agent.agent.gate import monitor_gate
    gate = monitor_gate(RuleFakeMonitor(), setting=setting, embedder=KeywordOnlyEmbedder(), task=task)
    sink = ListSink()
    run_agent(task, state, scripted_agent(task_id), gate=gate, user=ScriptedUser(confirms), on_event=sink)
    return [e.model_dump(mode="json") for e in sink.events], real_after, state


@pytest.mark.parametrize("task_id,confirms,setting", [
    ("demo_visible", True, "selective"), ("demo_hidden", True, "always"),
    ("demo_acmepay", True, "selective"), ("demo_acmepay", False, "selective"), ("demo_acmepay", True, "always")])
def test_state_at_every_step_equals_the_simulator(task_id, confirms, setting, monkeypatch):
    events, real_after, start = _run(task_id, confirms, setting, monkeypatch)
    assert events[0]["type"] == "company_snapshot"
    assert state_at(events, 0)["state"] == start.model_dump(mode="json")
    diff_steps = [e["step"] for e in events if e["type"] == "state_diff"]
    assert len(diff_steps) == len(real_after) >= 1
    for step, real in zip(diff_steps, real_after):
        assert state_at(events, step)["state"] == real
    end = state_at(events)["state"]
    assert end == real_after[-1]
    if task_id == "demo_acmepay":
        assert ("AcmePay" in end["repos"]) is (not confirms)        # yes: deleted; no: still there


def test_a_multi_write_episode_rebuilds_at_every_step(monkeypatch):
    """An agent (FakeLLM) making several different writes, all allowed: every step's state matches."""
    real_after = []
    real_diff = ev.state_diff
    def spy(before, after):
        real_after.append(after.model_dump(mode="json"))
        return real_diff(before, after)
    monkeypatch.setattr(ev, "state_diff", spy)
    replies = [assistant_msg(None, [ToolCall(id=f"c{i}", name=n, args=a)]) for i, (n, a) in enumerate(WRITES)]
    sink = ListSink()
    task = TASKS["demo_hidden"]
    run_agent(task, build_seed_state(0), FakeLLM(replies + [assistant_msg("done", [])]), gate=allow_all, on_event=sink)
    events = [e.model_dump(mode="json") for e in sink.events]
    steps = [e["step"] for e in events if e["type"] == "state_diff"]
    assert len(steps) == len(WRITES) == len(real_after)
    for step, real in zip(steps, real_after):
        assert state_at(events, step)["state"] == real


def test_old_logs_without_a_snapshot_say_so():
    with pytest.raises(ValueError, match="no company_snapshot"):
        state_at([{"type": "instruction", "step": 0, "payload": {}}])
