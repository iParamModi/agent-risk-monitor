"""Facts hidden from the monitor are shown to the human viewer (company_snapshot) but NEVER put into the monitor's
prompt, unless the monitor asked the gateway for them: it sees only what it checked (and what the agent's own tool
results showed). Unique marker values are planted in hidden fields of every record of the company, then every demo
task runs in selective and always; every marker in a prompt must come from an earlier gateway check result."""
import json
import re

import pytest

from lma_agent.agent.gate import monitor_gate
from lma_agent.agent.loop import run_agent
from lma_agent.agent.user_sim import ScriptedUser
from lma_agent.sim.seed_state import apply_overrides, build_seed_state
from lma_agent.tasks.load_tasks import load_tasks
from src.live.events import ListSink
from src.live.fake_monitor import RuleFakeMonitor
from src.live.monitor_gate import KeywordOnlyEmbedder
from src.live.scripted_agent import scripted_agent

TASKS = {t.task_id: t for t in load_tasks("lma_agent/tasks/demo_tasks.yaml")}
MARK = re.compile(r"ZZHIDDEN\w+ZZ")


def plant(state):
    """Free-text hidden fields (no read tool shows them) and every entity's hidden attrs get a unique marker."""
    n = 0

    def mark(tag):
        nonlocal n
        n += 1
        return f"ZZHIDDEN{tag}{n}ZZ"
    for f in state.files.values():
        f.retain_until, f.attrs = mark("retain"), {"note": mark("fileattr")}
    for c in state.customers.values():
        c.retain_until, c.attrs = mark("custretain"), {"note": mark("custattr")}
    for c in state.contacts.values():
        c.region, c.attrs = mark("region"), {"note": mark("contactattr")}
    for a in state.accounts.values():
        a.region, a.attrs = mark("accregion"), {"note": mark("accattr")}
    for r in state.repos.values():
        r.attrs = {"note": mark("repoattr")}
    for u in state.users.values():
        u.attrs = {"note": mark("userattr")}
    return n


class Spy:
    """The monitor model, recording each prompt with the gateway results the run had shown before it."""

    def __init__(self, sink):
        self.inner, self.sink, self.name, self.seen = RuleFakeMonitor(), sink, "spy", []

    def generate(self, messages):
        checked = " ".join(json.dumps(e.payload) for e in self.sink.events if e.type == "gateway_check")
        self.seen.append((json.dumps(messages), checked))
        return self.inner.generate(messages)


@pytest.mark.parametrize("task_id", sorted(TASKS))
@pytest.mark.parametrize("setting", ["selective", "always"])
def test_hidden_facts_reach_the_monitor_only_through_its_checks(task_id, setting):
    task = TASKS[task_id]
    state = apply_overrides(build_seed_state(task.state_seed), task.overrides)
    planted = plant(state)
    sink = ListSink()
    spy = Spy(sink)
    gate = monitor_gate(spy, setting=setting, embedder=KeywordOnlyEmbedder(), task=task)
    run_agent(task, state, scripted_agent(task_id), gate=gate, user=ScriptedUser(True), on_event=sink)

    snapshot = json.dumps(sink.events[0].payload)
    assert sink.events[0].type == "company_snapshot" and len(set(MARK.findall(snapshot))) == planted   # human sees all
    assert spy.seen, "the monitor ran"
    for prompt, checked in spy.seen:
        leaked = set(MARK.findall(prompt)) - set(MARK.findall(checked))
        assert not leaked, f"hidden facts in the monitor prompt without a check: {sorted(leaked)[:5]}"
        assert "company_snapshot" not in prompt and "hidden_from_monitor" not in prompt


def test_sharing_stays_hidden_until_checked_in_demo_hidden():
    """demo_hidden: the listing shows dates only, so the first pass must not see that report_7 is shared outside."""
    task = TASKS["demo_hidden"]
    state = apply_overrides(build_seed_state(task.state_seed), task.overrides)
    sink = ListSink()
    spy = Spy(sink)
    gate = monitor_gate(spy, setting="selective", embedder=KeywordOnlyEmbedder(), task=task)
    run_agent(task, state, scripted_agent("demo_hidden"), gate=gate, user=ScriptedUser(True), on_event=sink)
    first_prompt, checked_before = spy.seen[0]
    assert "external:globex" not in first_prompt and checked_before == ""
    assert "external:globex" in json.dumps(sink.events[0].payload)            # the human viewer sees it
    assert any("external:globex" in p for p, c in spy.seen[1:] if "external:globex" in c)   # after the check
