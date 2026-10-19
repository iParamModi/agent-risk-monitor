"""Loads task lists from YAML."""
from pathlib import Path

import yaml

from lma_agent.sim.models import Task

SMOKE_TASKS = Path(__file__).resolve().parent / "smoke_tasks.yaml"


def load_tasks(path: str | Path = SMOKE_TASKS) -> list[Task]:
    """Return the tasks in a YAML file (a list of Task dicts)."""
    with open(path) as fh:
        return [Task.model_validate(row) for row in yaml.safe_load(fh)]
