"""TEMPORARY policy store from docs/Policy.md + docs/Policy_OOD.md (until Param's Step 5 replaces it).

  python scripts/build_policies.py

Writes only the VISIBLE text (decisions.md R8.1): one {"policy_id", "text"} per line.
  data/policies/policies.jsonl      138 in-domain policies
  data/policies/policies_ood.jsonl  the OOD store: in-domain policies with the 26 reworded texts in
                                    place of their originals (same ID, as the OOD seeds use), plus
                                    the 14 new CUST policies
The other Policy.md columns (case, actions, fact, decision) are hidden logic and are NOT copied.
Texts are copied as written; wording is Param's (Step 5).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.common.io import REPO_ROOT, write_jsonl  # noqa: E402

IN_DOMAIN_MD = REPO_ROOT / "docs" / "Policy.md"
OOD_MD = REPO_ROOT / "docs" / "Policy_OOD.md"
OUT_DIR = REPO_ROOT / "data" / "policies"
ROW = re.compile(r"^\| `(P_[A-Z]+_\d+)` \|(.*)\|\s*$")


def table_rows(markdown: str) -> list[tuple[str, list[str]]]:
    """(policy_id, other cells) for every table row that starts with a policy ID."""
    out = []
    for line in markdown.splitlines():
        m = ROW.match(line)
        if m:
            out.append((m.group(1), [c.strip() for c in m.group(2).split("|")]))
    return out


def in_domain(markdown: str) -> list[dict]:
    """Policy.md rows: | id | text | case | actions | fact | decision | #seeds |"""
    return [{"policy_id": pid, "text": cells[0]} for pid, cells in table_rows(markdown)]


def ood(markdown: str, base: list[dict]) -> list[dict]:
    """Policy_OOD.md: CUST rows have 6 cells after the ID (text first); reworded rows have 4
    (domain, reworded text, in-domain text, fact). Reworded texts replace the in-domain ones."""
    reworded, cust = {}, []
    for pid, cells in table_rows(markdown):
        if len(cells) == 4:
            reworded[pid] = cells[1]
        else:
            cust.append({"policy_id": pid, "text": cells[0]})
    known = {p["policy_id"] for p in base}
    missing = sorted(set(reworded) - known)
    if missing:
        raise ValueError(f"reworded policies not in Policy.md: {missing}")
    return [{"policy_id": p["policy_id"], "text": reworded.get(p["policy_id"], p["text"])} for p in base] + cust


def check(policies: list[dict], name: str) -> None:
    ids = [p["policy_id"] for p in policies]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ValueError(f"{name}: duplicate policy IDs {dupes}")
    empty = [p["policy_id"] for p in policies if not p["text"]]
    if empty:
        raise ValueError(f"{name}: empty text for {empty}")


def style_notes(policies: list[dict]) -> list[str]:
    """Texts that do not start with a capital or end with a full stop (for Param to tidy)."""
    return [p["policy_id"] for p in policies if not (p["text"][:1].isupper() and p["text"].endswith("."))]


def main() -> int:
    base = in_domain(IN_DOMAIN_MD.read_text(encoding="utf-8"))
    ood_store = ood(OOD_MD.read_text(encoding="utf-8"), base)
    for name, policies in (("policies", base), ("policies_ood", ood_store)):
        check(policies, name)
        write_jsonl(OUT_DIR / f"{name}.jsonl", policies)
        print(f"{name}.jsonl: {len(policies)} policies")
    notes = style_notes(base)
    if notes:
        print(f"{len(notes)} in-domain texts without a capital start or full stop (for Param): {', '.join(notes)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
