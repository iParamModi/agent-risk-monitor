"""CLAUDE.md required checks: pytest blocks the network and refuses real-account approval; the repo holds no
hard-coded keys or tokens, and no Modal setting above the Tier B caps (or any keep-warm setting)."""
import socket
import subprocess

import pytest

from src.common.io import REPO_ROOT
from src.common.secret_scan import find_costly_modal_settings, find_secrets, uses_modal
from tests.conftest import NetworkBlocked, approval_problem

TEXT_SUFFIXES = {".py", ".md", ".txt", ".yaml", ".yml", ".json", ".jsonl", ".toml", ".cfg", ".ini", ".sh", ".ipynb",
                 ".csv", ".html", ".js", ".css", ".tex", ".bib", ""}
MAX_BYTES = 5_000_000
# Third-party safety benchmarks (R-Judge, ATBench, ...): their agent trajectories contain made-up credentials on
# purpose (leaking them is what the benchmark tests). Checked on 2026-11-13: all 543 scanner hits were there, none
# anywhere else. Everything else in the repo is scanned.
SKIP_PREFIXES = ("data/external/",)


def tracked_text_files():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=REPO_ROOT, capture_output=True, check=True).stdout
    for name in out.decode().split("\0"):
        path = REPO_ROOT / name
        if name and not name.startswith(SKIP_PREFIXES) and path.is_file() and path.suffix in TEXT_SUFFIXES and path.stat().st_size <= MAX_BYTES:
            yield name, path.read_text(encoding="utf-8", errors="replace")


# --- the conftest guards

def test_real_network_is_blocked():
    with pytest.raises(NetworkBlocked):
        socket.create_connection(("93.184.216.34", 80), timeout=1)
    with pytest.raises(NetworkBlocked):
        socket.getaddrinfo("api.groq.com", 443)


def test_loopback_still_works():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    try:
        client = socket.create_connection(server.getsockname(), timeout=2)
        client.close()
    finally:
        server.close()


def test_approval_in_the_shell_is_refused():
    assert approval_problem({}) is None
    assert "unset ALLOW_PAID_CALLS" in approval_problem({"ALLOW_PAID_CALLS": "anything"})


# --- the scanners themselves

@pytest.mark.parametrize("text", [
    "GROQ_API_KEY = 'gsk_" + "a1B2c3D4e5F6g7H8i9J0k1L2'",
    "token: hf_" + "abcdefghijklmnopqrstuvwxyzABCDEF",
    "-----BEGIN RSA " + "PRIVATE KEY-----",
    'api_key = "' + "x" * 24 + '"',
])
def test_scanner_finds_secrets(text):
    assert find_secrets(text)


def test_scanner_ignores_normal_text():
    assert not find_secrets('{"tokens_in": 974, "tokens_out": 16, "decision": "BLOCK"}')
    assert not find_secrets("GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')")


@pytest.mark.parametrize("line,bad", [
    ("min_containers=1", True), ("max_containers = 2", True), ("timeout=601", True),
    ("scaledown_window=300", True), ("keep_warm=1", True),
    ("min_containers=0", False), ("max_containers=1", False), ("timeout=600", False), ("scaledown_window=120", False),
])
def test_modal_settings_scanner(line, bad):
    assert bool(find_costly_modal_settings(f"import modal\n@app.function({line})\n")) is bad


# --- the repo

def test_no_hard_coded_secrets_in_tracked_files():
    hits = [(name, found) for name, text in tracked_text_files() for found in find_secrets(text)]
    assert not hits, f"possible secrets in tracked files: {hits}"


def test_no_costly_modal_settings_in_tracked_files():
    hits = [(name, bad) for name, text in tracked_text_files()
            if name.endswith(".py") and uses_modal(text) for bad in find_costly_modal_settings(text)]
    assert not hits, f"Modal settings above the Tier B caps (CLAUDE.md, ask Prateek): {hits}"
