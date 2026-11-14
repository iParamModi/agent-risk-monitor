"""GET /api/team: every part on the "How it works" page is tied to PROGRESS.md rows under that person's name."""
from fastapi.testclient import TestClient

from src.service.app import create_app
from src.service.team import TEAM, in_progress_file, progress_rows, team


def test_progress_tables_are_read():
    rows = progress_rows()
    assert len(rows) > 30 and all(task and who for task, who in rows)


def test_every_part_cites_rows_that_exist_under_that_person():
    rows = progress_rows()
    for name, short, parts in TEAM:
        for part, titles in parts:
            assert titles, f"{name}: {part} cites no PROGRESS.md row"
            for title in titles:
                assert in_progress_file(title, short, rows), f"{name}: no PROGRESS.md row '{title}' by {short}"


def test_the_four_people_and_all_their_parts_are_served():
    data = TestClient(create_app()).get("/api/team").json()
    assert [p["name"] for p in data["team"]] == ["Meet Ghelani", "Moiesha", "Param Modi", "Prateek Tiwari"]
    assert [len(p["parts"]) for p in data["team"]] == [len(parts) for _, _, parts in TEAM]
    assert "PROGRESS.md" in data["source"]


def test_a_part_is_dropped_when_its_row_is_gone(tmp_path):
    path = tmp_path / "PROGRESS.md"
    path.write_text("## Completed\n\n| Task | Done By | Date |\n|---|---|---|\n"
                    "| **Step 5: policy store** (all 4 outputs) | Param | 2026-10-26 |\n"
                    "| Step 12: evaluation code | Param | 2026-10-25 |\n\n## Blockers\n")
    people = {p["name"]: [x["part"] for x in p["parts"]] for p in team(path)["team"]}
    assert people["Param Modi"] == ["Policy store"]
    assert people["Meet Ghelani"] == [], "a row under another name does not count"
    assert all(p["parts"] == [] for p in team(tmp_path / "missing.md")["team"])


def test_report_pdf_is_served():
    res = TestClient(create_app()).get("/report.pdf")
    assert res.status_code == 200 and res.headers["content-type"] == "application/pdf"
