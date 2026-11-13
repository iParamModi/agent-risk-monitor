"""/api/results serves the report's numbers: every value, formatted the way the report formats it, equals the cell
in the rendered report tables (docs/reports/final_results_v2.md). Nothing is typed by hand."""
import re

import pytest
from fastapi.testclient import TestClient

from src.eval.tables import num, p_value, pct, with_ci
from src.service.app import create_app
from src.service.results import RESULTS_MD

MD_SPLIT = {"val": "Val", "test": "Test", "ood": "OOD"}


def md_sections() -> dict[str, list[list[str]]]:
    """'### <Split>, <policies>' -> every table row (cells) until the next heading."""
    out, current = {}, None
    for line in RESULTS_MD.read_text(encoding="utf-8").splitlines():
        if line.startswith("### "):
            current = line[4:].strip()
            out[current] = []
        elif current and line.startswith("| ") and not re.match(r"^\|\s*(Method|Model)\s*\|", line):
            out[current].append([c.strip() for c in line.strip().strip("|").split("|")])
    return out


@pytest.fixture(scope="module")
def results():
    return TestClient(create_app()).get("/api/results").json()


def test_results_name_their_source(results):
    assert results["source"] == "docs/reports/final_results_v2.json" and results["system"].startswith("v2")
    assert {t["split"] for t in results["tables"]} == {"val", "test", "ood"}
    assert {t["policies"] for t in results["tables"]} == {"retrieval", "gold"}


def test_every_number_matches_the_report_tables(results):
    sections = md_sections()
    checked = 0
    for t in results["tables"]:
        rows = sections[f"{MD_SPLIT[t['split']]}, {t['policies_name']}"]
        main = [r for r in rows if len(r) == 12]
        versus = [r for r in rows if len(r) == 6]
        assert len(main) == len(t["rows"]) and len(versus) == len(t["selective_vs_always"])
        for api, md in zip(t["rows"], main):
            assert md == [api["label"], api["setting"], with_ci(api["accuracy"]), pct(api["unsafe_action_rate"]),
                          pct(api["wrong_block_rate"]), pct(api["decision_macro_f1"]), num(api["checks_per_case"]),
                          pct(api["saving_vs_always"]), pct(api["check_precision"]), pct(api["check_recall"]),
                          pct(api["correct_missing_fact"]), str(api["invalid"])]
            checked += 1
        for api, md in zip(t["selective_vs_always"], versus):
            assert md[0] == api["label"]
            assert md[1] == f"{with_ci(api['unsafe_diff'])} (margin {pct(api['margin'])})"
            assert md[2] == ("**passes**" if api["hypothesis_passes"] else "fails")
            assert md[3] == with_ci(api["accuracy_diff"]) and md[4] == p_value(api["mcnemar_p"])
            assert md[5] == (f"{num(api['checks_selective'])} vs {num(api['checks_always'])} "
                             f"(p {p_value(api['checks_p'])})")
            checked += 1
    assert checked >= 6 * 10, "every table row was compared"


def test_tasks_endpoint_lists_the_preset_demo_tasks():
    tasks = TestClient(create_app()).get("/api/tasks").json()
    assert [t["id"] for t in tasks] == ["demo_visible", "demo_hidden", "demo_acmepay"]
    assert all(t["title"] and t["description"] and t["expected"]["decision"] for t in tasks)


def test_state_endpoint_steps_through_a_run():
    client = TestClient(create_app())
    run = next(r for r in client.get("/api/runs").json()
               if r["task"] == "demo_acmepay" and r["setting"] == "selective" and r["confirm"] == "yes")
    url = f"/api/runs/{run['source']}/{run['run_id']}/state"
    start, end = client.get(url, params={"step": 0}).json(), client.get(url).json()
    assert "AcmePay" in start["state"]["repos"] and "AcmePay" not in end["state"]["repos"]      # approved, deleted
    assert start["state"]["repos"]["AcmePay"]["production"] is True
    assert "production" in start["hidden_from_monitor"]["repos"] and end["diffs"]
    assert client.get(f"/api/runs/{run['source']}/nope/state").status_code == 404
