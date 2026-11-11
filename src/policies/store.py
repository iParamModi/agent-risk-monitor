"""Loads policies.jsonl: the visible policy text, the only policy text that reaches a prompt (R8.1)."""
from pathlib import Path

from src.common.io import REPO_ROOT, read_jsonl

POLICY_DIR = REPO_ROOT / "data" / "policies"
IN_DOMAIN = POLICY_DIR / "policies.jsonl"
OOD = POLICY_DIR / "policies_ood.jsonl"
TAGS = POLICY_DIR / "policy_tags.yaml"      # policy id -> tools it applies to (scripts/gen_policy_tags.py)


def load_policies(path: str | Path = IN_DOMAIN) -> list[dict]:
    """[{"policy_id", "text"}] in file order. Raises on a missing field or a duplicate ID."""
    policies = list(read_jsonl(path))
    seen = set()
    for p in policies:
        if not p.get("policy_id") or not p.get("text"):
            raise ValueError(f"{Path(path).name}: policy without policy_id or text: {p}")
        if p["policy_id"] in seen:
            raise ValueError(f"{Path(path).name}: duplicate policy_id {p['policy_id']}")
        seen.add(p["policy_id"])
    return policies


def load_policy_tags(path: str | Path = TAGS) -> dict[str, set[str]]:
    """policy id -> the agent tools the policy applies to. Metadata only: no condition, fact or decision."""
    import yaml
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return {pid: set(tools or []) for pid, tools in raw.items()}
