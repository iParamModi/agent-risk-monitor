"""The committed demo logs (outputs/live/demo/, real Kaggle runs and fake/) hold no keys, tokens, approval value or
machine paths, and every log says which agent and monitor system produced it (the replay website shows both)."""
import json
import re

import pytest

from src.common.io import REPO_ROOT
from src.common.secret_scan import find_secrets
from src.service.cost_guard import APPROVAL_VAR, APPROVED

DEMO = REPO_ROOT / "outputs" / "live" / "demo"
EXTRA = {
    "real-account approval value": re.compile(re.escape(APPROVED)),
    "approval variable": re.compile(re.escape(APPROVAL_VAR)),
    "secret env name with a value": re.compile(r"(GROQ_API_KEY|MODAL_TOKEN_\w+|LIVE_PASSWORD|HF_TOKEN|KAGGLE_KEY)\W+\w{8,}"),
    "home directory path": re.compile(r"/home/[A-Za-z0-9_.-]+/|/Users/[A-Za-z0-9_.-]+/"),
}


def demo_files():
    return sorted(p for p in DEMO.rglob("*") if p.is_file())


def test_there_are_demo_logs():
    assert any(p.suffix == ".jsonl" for p in demo_files()), "no demo logs in outputs/live/demo/"


@pytest.mark.parametrize("path", demo_files(), ids=lambda p: str(p.relative_to(DEMO)))
def test_demo_file_has_no_secrets(path):
    hits = find_secrets(path.read_text(encoding="utf-8", errors="replace"), extra=EXTRA)
    assert not hits, f"{path.relative_to(REPO_ROOT)}: {hits}"


@pytest.mark.parametrize("path", [p for p in demo_files() if p.suffix == ".jsonl" and p.parent.name != "attempts"],
                         ids=lambda p: str(p.relative_to(DEMO)))
def test_demo_log_names_agent_and_monitor_system(path):
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert events[0]["type"] == "company_snapshot" and events[0]["payload"]["hidden_from_monitor"]
    first = next(e for e in events if e["type"] == "instruction")
    meta = first["payload"]["meta"]
    assert meta["agent"] == "scripted" or meta["agent"].startswith("groq:")
    assert meta["monitor_version"] == "v2" and meta["k"] == 8
    assert isinstance(meta.get("fake_monitor"), bool)
    if meta["setting"] == "always":
        assert meta.get("trajectory_reused_from")
