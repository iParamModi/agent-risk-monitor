"""Recorded demo runs on CPU: Groq tries (a FakeLLM stands in for Groq), the scripted fallback, pauses, the log meta."""
import pytest

from lma_agent.agent.llm import FakeLLM, assistant_msg
from lma_agent.sim.models import ToolCall
from lma_agent.tasks.load_tasks import load_tasks
from src.live.demo_record import PLAN, SCRIPTED, GroqBudget, groq_name, record_run
from src.live.events import read_events
from src.live.fake_monitor import RuleFakeMonitor
from src.live.monitor_gate import KeywordOnlyEmbedder
from src.live.scripted_agent import scripted_agent

TASKS = {t.task_id: t for t in load_tasks("lma_agent/tasks/demo_tasks.yaml")}
GROQ = groq_name("openai/gpt-oss-120b")


def stalls(task_id):
    """A 'Groq' agent that looks around and stops without proposing the write."""
    return FakeLLM([assistant_msg(None, [ToolCall(id="c0", name="list_files", args={"folder": "/project"})]),
                    assistant_msg("I am not sure which files to delete.", [])]), GROQ


def does_it(task_id):
    return scripted_agent(task_id), GROQ


def fake_groq(*agents):
    calls = []

    def groq(task_id):
        calls.append(task_id)
        return agents[min(len(calls), len(agents)) - 1](task_id)
    groq.calls = calls
    return groq


def rec(task_id, tmp_path, groq, budget=None, confirm=None, setting="selective", **kw):
    sleeps = []
    row = record_run(TASKS[task_id], setting, confirm, model=RuleFakeMonitor(), embedder=KeywordOnlyEmbedder(),
                     out_dir=tmp_path, groq=groq, budget=budget or GroqBudget(5), max_tries=3, pause_s=65,
                     sleep=sleeps.append, log=lambda m: None, **kw)
    return row, sleeps, read_events(row["file"])


def test_plan_covers_every_demo_task_selective_first():
    assert {t for t, _, _ in PLAN} == set(TASKS)
    first = [s for _, s, _ in PLAN[:3]]
    assert first == ["selective"] * 3


def test_groq_that_reaches_the_write_is_kept(tmp_path):
    row, sleeps, events = rec("demo_hidden", tmp_path, fake_groq(does_it))
    meta = events[0]["payload"]["meta"]
    assert row["agent"] == GROQ and meta["agent"] == GROQ and meta["agent_attempt"] == 1
    assert meta["monitor_version"] == "v2" and meta["k"] == 8
    assert row["decision"] == "BLOCK" and row["match"] and row["checks_used"] == 1
    assert sleeps == []                                     # no pause before the session's first Groq episode
    assert row["prompt_tokens"] and all(t is not None for t in row["prompt_tokens"])


def test_groq_reaches_on_second_try_pauses_and_keeps_failed_try(tmp_path):
    row, sleeps, events = rec("demo_hidden", tmp_path, fake_groq(stalls, does_it))
    assert row["agent"] == GROQ and events[0]["payload"]["meta"]["agent_attempt"] == 2
    assert [t["reached_target"] for t in row["groq_attempts"]] == [False, True]
    assert sleeps == [65]
    assert (tmp_path / row["groq_attempts"][0]["file"]).exists()


def test_groq_never_reaches_falls_back_to_scripted_after_3_tries(tmp_path):
    groq = fake_groq(stalls)
    row, sleeps, events = rec("demo_acmepay", tmp_path, groq, confirm="no")
    meta = events[0]["payload"]["meta"]
    assert len(groq.calls) == 3 and len(row["groq_attempts"]) == 3
    assert row["agent"] == SCRIPTED and meta["agent"] == SCRIPTED
    assert "never proposed delete_repository in 3 tries" in meta["fallback_reason"]
    assert meta["monitor_version"] == "v2" and meta["k"] == 8
    assert row["decision"] == "ASK_CONFIRMATION" and row["confirm"] == "no"
    assert sleeps == [65, 65]
    assert len(list((tmp_path / "attempts").glob("*.jsonl"))) == 3


def test_budget_is_shared_and_stops_groq(tmp_path):
    budget = GroqBudget(2)
    groq = fake_groq(stalls)
    row, _, _ = rec("demo_visible", tmp_path, groq, budget=budget)
    assert len(groq.calls) == 2 and budget.left == 0
    assert row["agent"] == SCRIPTED and "budget used up" in row["fallback_reason"]
    row2, sleeps2, _ = rec("demo_hidden", tmp_path, groq, budget=budget)
    assert len(groq.calls) == 2 and row2["agent"] == SCRIPTED and sleeps2 == []


def test_groq_off_records_scripted(tmp_path):
    row, _, events = rec("demo_visible", tmp_path, None)
    assert row["agent"] == SCRIPTED and events[0]["payload"]["meta"]["fallback_reason"] == "Groq agent off"


def test_real_groq_agent_is_blocked_without_approval(tmp_path, monkeypatch):
    from src.live.demo_record import groq_agent
    from src.service.cost_guard import PaidCallBlocked
    monkeypatch.delenv("ALLOW_PAID_CALLS", raising=False)
    with pytest.raises(PaidCallBlocked):
        rec("demo_visible", tmp_path, groq_agent)
    assert not list(tmp_path.glob("*.jsonl"))              # nothing recorded, no silent scripted fallback


# --- fair comparison: always replays the selective run's agent trajectory, no new agent episode

def chatty(task_id):
    """A 'Groq' agent whose words and steps differ from the scripted one: an extra read before the delete."""
    return FakeLLM([
        assistant_msg("First I list the folder.", [ToolCall(id="g0", name="list_files", args={"folder": "/project"})]),
        assistant_msg("Let me look at the folder once more.",
                      [ToolCall(id="g1", name="list_files", args={"folder": "/project"})]),
        assistant_msg("report_7.pdf is older than June 2024, deleting it.",
                      [ToolCall(id="g2", name="delete_file", args={"file": "/project/report_7.pdf"})]),
        assistant_msg("Done, see above.", []),
    ]), GROQ


def plan_rows(tmp_path, groq, plan, budget=None):
    from src.live.demo_record import record_plan
    sleeps = []
    rows = record_plan(plan, TASKS, out_dir=tmp_path, model=RuleFakeMonitor(), embedder=KeywordOnlyEmbedder(),
                       groq=groq, budget=budget or GroqBudget(21), max_tries=3, pause_s=65, sleep=sleeps.append,
                       log=lambda m: None)
    return rows, sleeps


def test_default_groq_budget_is_5():
    from src.live.demo_record import DEFAULT_GROQ_BUDGET
    assert DEFAULT_GROQ_BUDGET == 5 and GroqBudget().total == 5


def test_always_reuses_the_selective_trajectory_without_a_new_agent_episode(tmp_path):
    import json
    groq = fake_groq(chatty)
    budget = GroqBudget(21)
    rows, sleeps = plan_rows(tmp_path, groq, [("demo_hidden", "selective", None), ("demo_hidden", "always", None)],
                             budget)
    sel, alw = rows
    assert len(groq.calls) == 1 and budget.used == 1 and sleeps == []        # no Groq episode for always
    assert alw["agent"] == sel["agent"] == GROQ and alw["reused_trajectory_from"] == sel["run_id"]
    meta = read_events(alw["file"])[0]["payload"]["meta"]
    assert meta["trajectory_reused_from"] == sel["run_id"] and meta["new_agent_episode"] is False
    assert meta["agent"] == GROQ and meta["setting"] == "always" and meta["k"] == 8

    def until_risky(row):
        out = []
        for e in read_events(row["file"]):
            if e["type"] in ("tool_call", "observation", "risk_action"):
                out.append((e["type"], json.dumps(e["payload"], sort_keys=True)))
            if e["type"] == "risk_action":
                return out
    assert until_risky(alw) == until_risky(sel)                    # same calls, same results, same risky action
    a = json.loads(open(alw["agent_messages_file"]).read())
    s = json.loads(open(sel["agent_messages_file"]).read())
    assert a["first_risky_index"] == s["first_risky_index"] == 2
    assert a["messages"][:3] == s["messages"][:3]                  # the agent's own words too (the monitor sees them)
    assert alw["checks_used"] == alw["checks_always"]              # only the monitor setting differs


def test_always_without_its_selective_run_fails_clearly(tmp_path):
    with pytest.raises(RuntimeError, match="record the selective run first"):
        plan_rows(tmp_path, None, [("demo_hidden", "always", None)])


def test_full_plan_uses_groq_only_for_selective_runs(tmp_path):
    groq = fake_groq(does_it)
    rows, _ = plan_rows(tmp_path, groq, PLAN)
    selective = [r for r in rows if r["setting"] == "selective"]
    always = [r for r in rows if r["setting"] == "always"]
    assert len(groq.calls) == len(selective) == 4
    assert all(r.get("reused_trajectory_from") for r in always)
    assert all(r["match"] for r in rows)
    acme = {r["confirm"]: r for r in always if r["task"] == "demo_acmepay"}
    src = {r["run_id"]: r for r in selective}
    assert src[acme["yes"]["reused_trajectory_from"]]["confirm"] == "yes"
