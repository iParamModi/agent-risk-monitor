import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("split_by_phase", ROOT / "scripts" / "split_by_phase.py")
sbp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sbp)

PHASES = sbp.load_phases(ROOT / "configs" / "tool_phases.yaml")


def msg(role, tool=None):
    return {"role": role, "text": "", "tool_call": {"name": tool, "args": {}} if tool else None, "action_text": None}


def record(rid, action, reads=(), split="train", set_="in_domain"):
    seed_id = rid.rsplit("-", 1)[0]
    traj = [msg("user")] + [msg("agent", t) for t in reads]
    return {"record_id": rid, "seed_id": seed_id, "source": "ours", "set": set_, "split": split,
            "visible": {"trajectory": traj, "proposed_action": {"name": action, "args": {}}}}


@pytest.mark.parametrize("action,reads,expected", [
    ("delete_file", ["list_files", "get_file_info"], "phase1"),  # 1
    ("delete_file", ["search_files"], "phase2"),                  # 2 phase 2 read anywhere
    ("pay_bill", [], "phase2"),                                   # 3
    ("archive_record", [], "ood"),                                # 4
    ("create_user", [], "rejected"),                              # 5 dropped
    ("frobnicate", [], "rejected"),                               # 6 unknown
    ("grant_access", [], "rejected"),                             # old name is not in the list
])
def test_bucket_for(action, reads, expected):
    assert sbp.bucket_for(record("IND-FILE-T1-001-A", action, reads), PHASES) == expected


def test_ood_seed_id_goes_to_ood_even_with_phase1_tools():
    assert sbp.bucket_for(record("OOD-FILE-T1-001-A", "delete_file", set_="ood"), PHASES) == "ood"


def test_split_kept_and_seed_records_stay_together():  # 7
    recs = [record("IND-FILE-T2-001-a", "share_file", ["get_file_info"], split="val"),
            record("IND-FILE-T2-001-c", "share_file", ["get_file_info", "create_event"], split="val"),
            record("IND-FILE-T1-002-A", "delete_file", split="test"),
            record("IND-FILE-T1-002-B", "delete_file", split="test")]
    out = sbp.split_records(recs, PHASES)
    assert [r["record_id"] for r in out["phase2"]] == ["IND-FILE-T2-001-a", "IND-FILE-T2-001-c"]
    assert [r["record_id"] for r in out["phase1"]] == ["IND-FILE-T1-002-A", "IND-FILE-T1-002-B"]
    assert {r["split"] for r in out["phase2"]} == {"val"} and {r["split"] for r in out["phase1"]} == {"test"}


def test_external_records_are_not_filtered():
    ext = {**record("IND-FILE-T1-001-A", "create_user"), "source": "r_judge"}
    assert all(not rows for rows in sbp.split_records([ext], PHASES).values())


def test_main_twice_gives_identical_files(tmp_path):  # 8
    rec_dir = tmp_path / "records"
    rec_dir.mkdir()
    rows = [record("IND-FILE-T1-001-A", "delete_file"), record("IND-FILE-T1-001-B", "delete_file", split="val"),
            record("IND-FIN-T1-001-A", "pay_bill"), record("OOD-CUST-T1-001-A", "archive_record", set_="ood"),
            record("IND-ACC-T1-001-A", "create_user")]
    sbp._write_jsonl(rec_dir / "all.jsonl", rows)
    seeds = tmp_path / "seeds"
    (seeds / "in_domain").mkdir(parents=True)
    outs = []
    for run in ("a", "b"):
        out = tmp_path / run
        assert sbp.main(["--in", str(rec_dir), "--out", str(out), "--seeds", str(seeds)]) == 0
        outs.append({p.name: p.read_text() for p in sorted(out.iterdir())})
    assert outs[0] == outs[1]
    files = outs[0]
    assert len(files["phase1_train.jsonl"].splitlines()) == 1 and len(files["phase1_val.jsonl"].splitlines()) == 1
    assert "IND-FIN-T1-001-A" in files["phase2_train.jsonl"] and "OOD-CUST" in files["ood_test.jsonl"]
    assert "create_user" in files["split_summary.json"] and "OOD record OOD-CUST-T1-001-A is marked train" in files["split_summary.json"]


def test_seed_bucket_uses_every_subtype():
    seed = {"seed_id": "IND-FILE-T2-001", "proposed_action": {"name": "share_file", "args": {}},
            "t2_subtypes": {"a": {"earlier_read": {"tool": "get_file_info"}, "later_write": None},
                            "c": {"earlier_read": {"tool": "get_file_info"},
                                  "later_write": {"name": "create_event", "args": {}}},
                            "d": None}}
    assert sbp.bucket_for_seed(seed, PHASES) == ("phase2", ["create_event"])


def test_tool_in_two_lists_is_an_error(tmp_path):
    p = tmp_path / "phases.yaml"
    p.write_text(yaml.safe_dump({"phase1_in_domain": {"read": ["a"], "write": []}, "ood_test_only": {},
                                 "phase2": {"read": ["a"]}, "dropped": []}))
    with pytest.raises(ValueError):
        sbp.load_phases(p)


def test_agent_tools_yaml_agrees_with_tool_phases():
    specs = yaml.safe_load((ROOT / "lma_agent" / "tools.yaml").read_text())
    for name, spec in specs.items():
        if spec.get("ood"):
            assert name in PHASES["ood"], name
        elif spec["phase"] == 1:
            assert name in PHASES["phase1"], name
        else:
            assert name in PHASES["phase2"], name
    assert PHASES["phase1"] <= set(specs), sorted(PHASES["phase1"] - set(specs))
