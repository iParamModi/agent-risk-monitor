"""Loads the raw ATBench test.json from data/raw/atbench."""
import json
from pathlib import Path

from src.common.io import REPO_ROOT

ATBENCH_FILE = REPO_ROOT / "data" / "raw" / "atbench" / "ATBench" / "test.json"


def load_atbench(path: Path = ATBENCH_FILE) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run `make external`")
    return json.loads(path.read_text(encoding="utf-8"))
