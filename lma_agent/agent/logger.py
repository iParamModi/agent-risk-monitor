"""Step logs and episode files."""
import copy
import uuid
from datetime import datetime
from pathlib import Path

from lma_agent.config import RUNS_DIR
from lma_agent.sim.models import EpisodeResult, StepLog, ToolCall


def new_episode_id(task_id: str) -> str:
    """Return a unique, sortable episode id like smoke_file_01_20261019-142501_ab12."""
    return f"{task_id}_{datetime.now():%Y%m%d-%H%M%S}_{uuid.uuid4().hex[:4]}"


def make_step_log(episode_id: str, step: int, messages: list[dict], call: ToolCall, tool_type: str,
                  decision: str | None, state_hash_before: str, executed: bool, result: dict) -> StepLog:
    """Build one StepLog; the trajectory is copied so later messages don't leak into it."""
    return StepLog(episode_id=episode_id, step=step, trajectory_so_far=copy.deepcopy(messages),
                   proposed_action=call, tool_type=tool_type, gate_decision=decision,
                   state_hash_before=state_hash_before, executed=executed, result=result)


def save_episode(result: EpisodeResult, out_dir: str | Path = RUNS_DIR) -> Path:
    """Write the episode to <out_dir>/<episode_id>.json and return the path."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{result.episode_id}.json"
    path.write_text(result.model_dump_json(indent=2))
    return path
