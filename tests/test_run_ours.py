"""Our records through the monitor: CaseInputs (retrieval, check tools, gateway, always checks), the always setting's
filled table checks, and the traces run.py writes (src/monitor/run.py, src/monitor/case_inputs.py)."""
import json

import pytest

from src.common.io import REPO_ROOT, read_jsonl
from src.monitor.case_inputs import CaseInputs
from src.monitor.loop import run_monitor
from src.monitor.models import FakeModel
from src.monitor.run import Recording, RecordingGateway, scripted_answers, trace


class FakeEmbedder:
    """Same vector for everything: retrieval falls back to BM25 order, no model download."""

    def encode(self, texts, is_query=False):
        return [[1.0, 0.0] for _ in texts]


@pytest.fixture(scope="module")
def records():
    rows = list(read_jsonl(REPO_ROOT / "data" / "records" / "val.jsonl"))
    t1 = next(r for r in rows if r["case_type"] == "T1" and r["gold"]["required_checks"])
    t3 = next(r for r in rows if r["case_type"] == "T3")
    return t1, t3


@pytest.mark.parametrize("setting", ["never", "always", "selective", "oracle"])
def test_all_settings_run_on_our_records(records, setting):
    inputs = CaseInputs(embedder=FakeEmbedder())
    for rec in records:
        kwargs = inputs.for_record(rec, setting)
        kwargs["gateway"] = RecordingGateway(kwargs["gateway"])
        model = Recording(FakeModel(scripted_answers(setting, kwargs["table_checks"])))
        row = run_monitor(rec, setting, model, **kwargs)
        assert row["output"] is not None and len(kwargs["policies"]) == 3
        calls = kwargs["gateway"].calls
        if setting == "always":
            assert [c["tool"] for c in calls] == [c["tool"] for c in kwargs["table_checks"]]
        if setting == "oracle":
            assert [c["tool"] for c in calls] == [c["tool"] for c in rec["gold"]["required_checks"] or []]
            assert all("error" not in c["result"] for c in calls)
        if setting == "never":
            assert calls == []
        t = trace(rec, setting, kwargs, model.passes, calls, row)
        assert t["passes"] and t["passes"][0]["answer"] == model.texts[0]
        prompt = json.dumps([p["messages"] for p in t["passes"]])
        assert not any(p["policy_id"] in prompt for p in t["shown_policies"])     # ids never in a prompt
        assert "SECRET" not in prompt and rec["gold"]["decision"] in ("ALLOW", "BLOCK", "ASK_CONFIRMATION", "ESCALATE")


def test_always_uses_the_filled_table_checks_even_without_check_table(records):
    rec = records[0]
    inputs = CaseInputs(embedder=FakeEmbedder()).for_record(rec, "always")
    row = run_monitor(rec, "always", FakeModel(scripted_answers("always", [])), **inputs)
    assert [c["tool"] for c in row["calls"]] == [c["tool"] for c in inputs["table_checks"]]


def test_gold_policy_mode_shows_the_gold_policy_plus_look_alikes(records):
    for rec in records:
        shown = CaseInputs(embedder=FakeEmbedder(), policy_mode="gold").policies(rec)
        ids = [p["policy_id"] for p in shown]
        assert len(ids) == 3 and len(set(ids)) == 3 and all(g in ids for g in rec["gold"]["policy_ids"])
    with pytest.raises(ValueError):
        CaseInputs(policy_mode="oracle")
