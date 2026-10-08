"""src/common/io.py helpers."""
import json

from src.common.io import read_jsonl, write_jsonl, write_record_files


def test_jsonl_round_trip(tmp_path):
    rows = [{"record_id": "ATB-1", "text": "Café"}, {"record_id": "ATB-2", "text": "x"}]
    assert write_jsonl(tmp_path / "a.jsonl", rows) == 2
    assert list(read_jsonl(tmp_path / "a.jsonl")) == rows


def test_record_files_one_per_record_and_stale_removed(tmp_path):
    folder = tmp_path / "atbench"
    folder.mkdir()
    (folder / "ATB-999.json").write_text("{}")  # left over from an older run
    rows = [{"record_id": "ATB-1", "text": "Café"}, {"record_id": "ATB-2", "text": "x"}]
    assert write_record_files(folder, rows) == 2
    assert sorted(p.name for p in folder.glob("*.json")) == ["ATB-1.json", "ATB-2.json"]
    text = (folder / "ATB-1.json").read_text(encoding="utf-8")
    assert "Café" in text and "\n  " in text  # readable: real characters, indented
    assert json.loads(text) == rows[0]
