"""Gateway spec test 13, no bypass: the monitor, the settings, the rule baselines and the training-data builders
reach the environment only through src/gateway. A static scan of src/ fails on any read of a record's hidden
state, of a simulator state's fields, or of the gateway's internals outside the allow-list below.
"""
import re

from src.common.io import REPO_ROOT

SRC = REPO_ROOT / "src"

HIDDEN = re.compile(r"""\[\s*["']hidden["']\s*\]|\.get\(\s*["']hidden["']|\.hidden\b""")
STATE_FIELDS = re.compile(r"\bstate\.(files|folders|users|contacts|permissions|accounts|repos|customers|inbox|"
                          r"owner_approvals|events|exports|sent)\b")
INTERNALS = re.compile(r"src\.gateway\.(checks|record_state)\b|\b(CHECK_FUNCS|state_from_record)\b")

# Record generation and its quality checks write and inspect the hidden state; they build records, they never
# decide on one.
HIDDEN_ALLOWED = {"src/data_gen/merge.py", "src/data_gen/leakage_check.py", "src/data_gen/auto_checks.py"}


def _sources():
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if not rel.startswith("src/gateway/"):
            yield rel, path.read_text(encoding="utf-8")


def _hits(pattern, allowed=frozenset()):
    return [f"{rel}:{n}: {line.strip()}" for rel, text in _sources() if rel not in allowed
            for n, line in enumerate(text.splitlines(), 1) if pattern.search(line)]


def test_13_no_hidden_state_reads_outside_the_gateway():
    assert not _hits(HIDDEN, HIDDEN_ALLOWED)


def test_13_no_state_field_reads_outside_the_gateway():
    assert not _hits(STATE_FIELDS)


def test_13_no_gateway_internals_outside_the_gateway():
    assert not _hits(INTERNALS)


def test_a6_noise_never_in_training_data():
    assert not [rel for rel, text in _sources() if rel.startswith("src/training/") and "noise" in text.lower()]


def test_13_the_scan_finds_a_planted_read():
    """The patterns catch the reads they are meant to catch."""
    lines = ['x = record["hidden"]["state"]', "f = state.files[path]", "from src.gateway.checks import stated"]
    assert HIDDEN.search(lines[0]) and STATE_FIELDS.search(lines[1]) and INTERNALS.search(lines[2])
