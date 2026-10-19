import json

from lma_agent.agent.logger import make_step_log, new_episode_id, save_episode
from lma_agent.sim.models import EpisodeResult, ToolCall


def test_step_log_copies_trajectory():
    msgs = [{"role": "user", "content": "hi"}]
    log = make_step_log("e1", 1, msgs, ToolCall(id="c", name="read_file", args={"path": "/a"}),
                        "read", None, "h", True, {"ok": 1})
    msgs.append({"role": "tool"})
    assert len(log.trajectory_so_far) == 1 and log.tool_type == "read" and log.gold_decision is None


def test_save_episode(tmp_path):
    ep = EpisodeResult(episode_id=new_episode_id("t1"), task_id="t1", status="done", final_answer="ok",
                       messages=[], steps=[], n_llm_calls=1, n_tool_errors=0, final_state_hash="h")
    path = save_episode(ep, tmp_path)
    assert path.name == f"{ep.episode_id}.json" and ep.episode_id.startswith("t1_")
    assert json.loads(path.read_text())["status"] == "done"
