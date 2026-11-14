"""scripts/demo_table.py: the recorded demo runs are checked, and the report's demo table comes from summary.json."""
import json
import shutil

import pytest

from scripts import demo_table as dt
from src.service.app import DEMO_DIR

FAKE = DEMO_DIR / "fake"


@pytest.fixture
def folder(tmp_path):
    out = tmp_path / "demo"
    shutil.copytree(FAKE, out)
    return out


def edit_log(path, change):
    events = [json.loads(line) for line in path.read_text().splitlines()]
    events = change(events) or events
    path.write_text("".join(json.dumps(e) + "\n" for e in events))


def first_log(folder, setting="selective"):
    rows = json.loads((folder / "summary.json").read_text())
    return folder / next(r["file"] for r in rows if r["setting"] == setting)


def test_the_committed_fake_runs_pass_every_check():
    rows, problems = dt.load(FAKE)
    assert len(rows) == 7 and problems == []
    assert dt.replay_check(rows, FAKE) == []


def test_a_wrong_k_is_caught(folder):
    def change(events):
        for e in events:
            if e["type"] == "decision":
                e["payload"]["k"] = 3
    edit_log(first_log(folder), change)
    assert any("k=3" in p for p in dt.load(folder)[1])


def test_a_missing_snapshot_is_caught(folder):
    edit_log(first_log(folder), lambda events: [e for e in events if e["type"] != "company_snapshot"])
    problems = dt.load(folder)[1]
    assert any("company_snapshot" in p for p in problems) and any("does not rebuild" in p for p in problems)


def test_an_unknown_agent_label_is_caught(folder):
    def change(events):
        for e in events:
            if e["type"] == "instruction":
                e["payload"]["meta"]["agent"] = "some-model"
    edit_log(first_log(folder), change)
    assert any("agent label" in p for p in dt.load(folder)[1])


def test_an_event_outside_the_schema_is_caught(folder):
    def change(events):
        events[2]["type"] = "made_up"
    edit_log(first_log(folder), change)
    assert any("not a valid event log" in p for p in dt.load(folder)[1])


def test_a_summary_that_disagrees_with_its_log_is_caught(folder):
    rows = json.loads((folder / "summary.json").read_text())
    rows[0]["decision"] = "ALLOW"
    (folder / "summary.json").write_text(json.dumps(rows))
    assert any("summary.json decision" in p for p in dt.load(folder)[1])


def test_an_always_run_without_its_selective_run_is_caught(folder):
    rows = json.loads((folder / "summary.json").read_text())
    gone = next(r for r in rows if r["setting"] == "selective")
    (folder / "summary.json").write_text(json.dumps([r for r in rows if r is not gone]))
    problems = dt.load(folder)[1]
    assert any("not in this folder" in p for p in problems) and any("does not list" in p for p in problems)


def test_fake_runs_are_refused_for_the_report(folder, tmp_path, capsys):
    out = tmp_path / "table.md"
    assert dt.main(["--runs", str(folder), "--out", str(out)]) == 1
    assert not out.exists() and "fake-monitor runs are not report results" in capsys.readouterr().out


def test_table_has_the_report_columns_and_one_row_per_run(folder, tmp_path):
    out = tmp_path / "table.md"
    assert dt.main(["--runs", str(folder), "--out", str(out), "--allow-fake"]) == 0
    text = out.read_text()
    lines = [x for x in text.splitlines() if x.startswith("|")]
    assert lines[0] == "| task | agent | setting | checks used | checks always | decision | expected | match | latency |"
    assert len(lines) == 2 + 7
    rows = json.loads((folder / "summary.json").read_text())
    for row, line in zip(rows, lines[2:]):
        cells = [c.strip() for c in line.strip("|").split("|")]
        assert cells[2:6] == [row["setting"], str(row["checks_used"]), str(row["checks_always"]), row["decision"]]
        assert cells[7] == "yes"
    assert "FAKE monitor" in text and "7 of 7 runs" in text


def test_the_text_names_a_real_monitor_and_a_groq_agent_from_the_logs(folder):
    rows = json.loads((folder / "summary.json").read_text())
    for row in rows:
        def change(events):
            meta = next(e for e in events if e["type"] == "instruction")["payload"]["meta"]
            meta.update({"fake_monitor": False, "monitor_model": "Some/Model-8B", "adapter_dataset": "owner/adapter",
                         "recorded_on": "kaggle", "agent": "groq:vendor/agent-model"})
        edit_log(folder / row["file"], change)
        row["agent"] = "groq:vendor/agent-model"
        row.pop("fallback_reason", None)
    (folder / "summary.json").write_text(json.dumps(rows))
    assert dt.load(folder)[1] == []
    text = dt.describe(rows, folder)
    assert "FAKE" not in text and "Some/Model-8B" in text and "owner/adapter" in text
    assert "Groq vendor/agent-model agent in 4 runs" in text and "other 3 runs" in text
    assert text.count(". ") == 2          # three sentences


def test_a_wrong_check_count_shows_in_the_match_cell():
    row = {"setting": "selective", "match": True, "checks_used": 2, "expected_checks": 1, "checks_always": 5,
           "expected_decision": "BLOCK"}
    assert dt.match_text(row) == "decision yes, checks no" and dt.expected_text(row) == "BLOCK, 1 check"
    assert dt.match_text({**row, "match": False}) == "no"
    assert dt.match_text({**row, "setting": "always", "checks_used": 5}) == "yes"
