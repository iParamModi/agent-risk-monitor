"""Patterns for things that must never be committed (CLAUDE.md, Cost safety): keys and tokens, and Modal settings
that could cost money (min_containers > 0, max_containers > 1, timeout > 600, scaledown_window > 120, keep-warm).

    find_secrets(text)                -> [(name, matched text shortened)]
    find_costly_modal_settings(text)  -> [(setting, value)]   for files that use Modal
Used by tests/test_repo_safety.py (the whole repo) and tests/test_demo_logs_clean.py (the committed demo logs).
"""
import re

SECRET_PATTERNS: dict[str, re.Pattern] = {
    "Groq API key": re.compile(r"gsk_[A-Za-z0-9]{20,}"),
    "Hugging Face token": re.compile(r"\bhf_[A-Za-z0-9]{30,}"),
    "OpenAI-style secret key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    "Modal token id": re.compile(r"\bak-[A-Za-z0-9]{16,}"),
    "Modal token secret": re.compile(r"\bas-[A-Za-z0-9]{16,}"),
    "Kaggle API token": re.compile(r"\bKGAT_[A-Za-z0-9]{16,}"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "bearer token": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{20,}"),
    "key assigned in code": re.compile(
        r"(?i)\b[A-Z0-9_]*(api[_-]?key|secret|token|password)\b[\"']?\s*[:=]\s*[\"'][A-Za-z0-9_\-./+]{20,}[\"']"),
}

MODAL_LIMITS = {"min_containers": 0, "max_containers": 1, "timeout": 600, "scaledown_window": 120}
_MODAL_SETTING = re.compile(r"\b(min_containers|max_containers|timeout|scaledown_window)\s*=\s*(\d+(?:\.\d+)?)")
_KEEP_WARM = re.compile(r"\b(keep_warm|warm_pool_size|buffer_containers)\s*=\s*([^\s,)]+)")
_USES_MODAL = re.compile(r"^\s*(import modal\b|from modal\b)", re.MULTILINE)


def _short(text: str) -> str:
    return text if len(text) <= 12 else text[:6] + "..." + text[-2:]


def find_secrets(text: str, extra: dict[str, re.Pattern] | None = None) -> list[tuple[str, str]]:
    found = []
    for name, pattern in {**SECRET_PATTERNS, **(extra or {})}.items():
        found += [(name, _short(m.group(0))) for m in pattern.finditer(text)]
    return found


def uses_modal(text: str) -> bool:
    return bool(_USES_MODAL.search(text))


def find_costly_modal_settings(text: str) -> list[tuple[str, str]]:
    """Settings above the Tier B caps, and any keep-warm setting, in a file that uses Modal."""
    bad = [(name, value) for name, value in _MODAL_SETTING.findall(text) if float(value) > MODAL_LIMITS[name]]
    bad += [(name, value) for name, value in _KEEP_WARM.findall(text) if value not in ("0", "None", "False")]
    return bad
