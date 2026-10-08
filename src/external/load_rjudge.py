"""Loads the raw R-Judge JSON files from data/raw/r_judge."""
import json
from pathlib import Path
from typing import Iterator

from src.common.io import REPO_ROOT

RJUDGE_DATA = REPO_ROOT / "data" / "raw" / "r_judge" / "data"


def load_rjudge(data_dir: Path = RJUDGE_DATA) -> Iterator[tuple[str, dict]]:
    """Yields (path relative to data_dir, e.g. 'Program/security.json', raw record)."""
    files = sorted(data_dir.glob("*/*.json"))
    if not files:
        raise FileNotFoundError(f"no R-Judge files under {data_dir}; run `make external`")
    for f in files:
        rel = f.relative_to(data_dir).as_posix()
        for raw in json.loads(f.read_text(encoding="utf-8")):
            yield rel, raw
