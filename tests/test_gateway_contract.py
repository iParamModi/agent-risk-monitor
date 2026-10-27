"""Contract of the check gateway (Prateek, Step 4) for its users: src/monitor/loop.py (run_monitor(gateway=...))
and src/training/build_sft.py (Phase B second-pass results). Skipped until src/gateway/gateway.py has for_record.

    gateway = for_record(record)        # reads record["hidden"] and record["set"] only, never gold
    result = gateway.call(tool, args)   # always a dict; errors are data: {"error": <name>, ...} (R7.3, R7.4)
"""
import pytest
import yaml

from src.common.io import REPO_ROOT, read_jsonl
from src.monitor.loop import ERROR_NAMES

gateway = pytest.importorskip("src.gateway.gateway")
if not hasattr(gateway, "for_record"):
    pytest.skip("src/gateway/gateway.py has no for_record yet (Prateek, Step 4)", allow_module_level=True)

SPECS = yaml.safe_load((REPO_ROOT / "configs" / "check_tools.yaml").read_text(encoding="utf-8"))
RECORDS = [r for name in ("all_in_domain", "all_ood") for r in read_jsonl(REPO_ROOT / "data" / "records" / f"{name}.jsonl")]


def first(pred):
    return next(r for r in RECORDS if pred(r))


def test_errors_are_data_with_the_r7_names():
    g = gateway.for_record(first(lambda r: r["set"] == "in_domain" and r["hidden"]["state"].get("files")))
    calls = {"unknown_tool": ("check_nothing", {}), "write_not_allowed": ("delete_file", {"file": "x.pdf"}),
             "invalid_args": ("check_file_sharing", {}), "not_found": ("check_file_sharing", {"path": "/zz/none.txt"})}
    for name, (tool, args) in calls.items():
        out = g.call(tool, args)
        assert isinstance(out, dict) and out.get("error") == name and name in ERROR_NAMES, (tool, out)


def test_ood_only_tools_are_unknown_in_domain():
    ood_only = [t for t, spec in SPECS.items() if spec.get("ood")]
    g = gateway.for_record(first(lambda r: r["set"] == "in_domain"))
    for tool in ood_only:
        assert g.call(tool, {p: "x" for p in SPECS[tool]["params"]}).get("error") == "unknown_tool", tool


def test_every_gold_check_answers_with_only_its_return_fields():
    filled = [r for r in RECORDS if r["gold"]["required_checks"]]
    if not filled:
        pytest.skip("gold.required_checks not filled yet (Param, seed_to_record.md D4)")
    for r in filled:
        g = gateway.for_record(r)
        for c in r["gold"]["required_checks"]:
            out = g.call(c["tool"], c["args"])
            assert isinstance(out, dict) and "error" not in out, (r["record_id"], c, out)
            assert set(out) <= set(SPECS[c["tool"]]["returns"]), (r["record_id"], c, out)   # no other hidden field


def test_gateway_never_reads_gold():
    rec = dict(first(lambda r: r["gold"]["check_needed"]), gold=None)
    assert isinstance(gateway.for_record(rec).call("check_nothing", {}), dict)
