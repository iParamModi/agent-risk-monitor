import pytest

from lma_agent.agent.llm import FakeLLM, assistant_msg
from lma_agent.config import RUNS_DIR
from lma_agent.scripts import run_smoke
from lma_agent.scripts.run_smoke import GATES, compare_tools, format_table, summarize
from lma_agent.agent.loop import run_agent
from lma_agent.sim.models import ToolCall
from lma_agent.sim.seed_state import build_seed_state
from lma_agent.tasks.load_tasks import load_tasks

FIN = next(t for t in load_tasks() if t.task_id == "smoke_fin_01")


def fin_script():
    def c(i, name, **args):
        return assistant_msg(None, [ToolCall(id=f"c{i}", name=name, args=args)])
    return FakeLLM([
        c(1, "get_account", account_id="ACC-OPS"),
        c(2, "transfer_money", from_account="ACC-OPS", to_account="ACC-VENDOR-1", amount_inr=75000),
        assistant_msg("Paid.", []),
    ])


def test_compare_tools():
    assert compare_tools(["list_files", "delete_file"], ["list_files", "get_file_info", "delete_file"]) == {
        "ok": True, "missing": [], "extra": ["get_file_info"]}
    assert compare_tools(["get_account", "transfer_money"], ["transfer_money"])["missing"] == ["get_account"]


# Step 13: what each --gate does to the same scripted run.
@pytest.mark.parametrize("gate,status,writes", [
    ("allow", "done", 1), ("block", "done", 0), ("ask", "done", 1), ("escalate", "escalated", 0),
])
def test_gate_branches(gate, status, writes):
    res = run_agent(FIN, build_seed_state(0), fin_script(), gate=GATES[gate])
    row = summarize(FIN, res)
    assert row["status"] == status and row["writes_done"] == writes
    assert row["tools_used"] == "get_account,transfer_money" and row["expected_ok"]


def test_format_table():
    res = run_agent(FIN, build_seed_state(0), fin_script())
    out = format_table([summarize(FIN, res)])
    assert "smoke_fin_01" in out and "expected tools used: 1/1 tasks" in out


def test_main_with_fake_client(monkeypatch, tmp_path):
    monkeypatch.setattr(run_smoke, "make_client", fin_script)
    monkeypatch.setattr(run_smoke, "RUNS_DIR", tmp_path)
    rows = run_smoke.main(["--task", "smoke_fin_01", "--gate", "allow"])
    assert rows[0]["status"] == "done" and rows[0]["expected_ok"]
    assert (tmp_path / f"{rows[0]['episode_id']}.json").exists()
    assert RUNS_DIR.name == "runs"


@pytest.mark.live
def test_live_smoke_all_done():
    rows = run_smoke.main([])
    assert all(r["status"] == "done" for r in rows)
