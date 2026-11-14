"""Who built which part, for the workspace's "How it works" page (GET /api/team).

Nothing here is a claim of its own: every part names the PROGRESS.md rows it comes from (the Completed and In
Progress tables), and team() returns a part only while each of those rows is still in PROGRESS.md under that
person's name. tests/test_team_api.py fails when a row is renamed or moved to someone else, so the page cannot drift
from the team's own record.
"""
import re

from src.common.io import REPO_ROOT

PROGRESS = REPO_ROOT / "PROGRESS.md"
TABLES = ("## In Progress", "## Completed")
# (full name, name in PROGRESS.md, ((part, (titles of the PROGRESS.md rows it sums up, as substrings)), ...))
TEAM = (
    ("Meet Ghelani", "Meet", (
        ("External data: R-Judge, ATBench and AgentRisk downloaded, normalised, split and risk-typed",
         ("Step 7: external data", "AgentRisk (SemEval) data")),
        ("Evaluation code", ("Step 12: evaluation code",)),
        ("Monitor training: Phase A and the Phase B training-file builder",
         ("Step 16 + 17 (Phase A)", "Phase B SFT builder")),
        ("Record merge, the locked split and the leakage checks",
         ("Step 9 merge + Step 11 split/lock + leakage checks",)),
        ("System v2 (retrieval and checking), the final runs and the error analysis",
         ("System v2: improve retrieval and checking", "Collected test + OOD runs + error analysis")),
        ("Final report draft", ("Final report draft",)),
    )),
    ("Moiesha", "Moiesha", (
        ("Seeds: in-domain T2 and T3, reviewed and diversified",
         ("Step 8: in-domain T2 seeds", "Step 8: in-domain T3 seeds")),
        ("R-Judge risk-type review", ("R-Judge risk-type review (237 rows)",)),
    )),
    ("Param Modi", "Param", (
        ("Seeds: in-domain T1, T4 and T5, and the out-of-domain set",
         ("Step 8: in-domain T1 seeds", "Step 8: in-domain T4 (15) + T5 (22) seeds", "Step 8: OOD seeds authored")),
        ("Policy store", ("Step 5: policy store",)),
        ("Seed cleanup and more T5 seeds where two checks disagree",
         ("Seed cleanup: align all 174 seeds", "More T5 facts_disagree seeds")),
    )),
    ("Prateek Tiwari", "Prateek", (
        ("The demo company and its tools (lma_agent), in the seed vocabulary",
         ("Demo company (`lma_agent`) changed to the seed vocabulary",)),
        ("Check tools, the check table and the read-only gateway",
         ("Check tools + check table installed", "Check gateway part 2")),
        ("Tool phases and the seed split", ("Tool phases + seed split",)),
        ("Deployment demo: live gate, recorded runs and this workspace", ("Deployment demo",)),
    )),
)


def progress_rows(path=PROGRESS) -> list[tuple[str, str]]:
    """(task, who) of every row of the In Progress and Completed tables; [] when the file is missing."""
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    rows = []
    for head in TABLES:
        start = text.find(head)
        if start < 0:
            continue
        end = text.find("\n## ", start + 1)
        for line in text[start:end if end > 0 else len(text)].splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
            if line.startswith("| ") and len(cells) >= 2 and not set(cells[0]) <= set("-: "):
                rows.append((cells[0].replace("**", ""), cells[1]))
    return rows


def in_progress_file(title: str, who: str, rows: list[tuple[str, str]]) -> bool:
    return any(title in task and re.search(rf"\b{re.escape(who)}\b", person) for task, person in rows)


def team(path=PROGRESS) -> dict:
    rows = progress_rows(path)
    people = [{"name": name,
               "parts": [{"part": part, "progress_rows": list(titles)} for part, titles in parts
                         if all(in_progress_file(t, short, rows) for t in titles)]}
              for name, short, parts in TEAM]
    return {"source": "PROGRESS.md (In Progress and Completed tables)", "team": people}
