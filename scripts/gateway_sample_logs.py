"""One T2 case through the gateway in all four settings, written as gateway_log.jsonl (gateway spec §10).

    python scripts/gateway_sample_logs.py [record_id]     # default: the first val T2 record with a gold check

never: no call (empty log). always: run_always. oracle: run_oracle. selective: a SCRIPTED monitor, not a model
run: one call with a wrong argument name (the base model's real mistake, `file` for `path`, or a missing field),
then the gold checks, within the 4-call cap. Writes docs/gateway_samples/gateway_log.jsonl (all settings, in
order) and prints each setting's summary.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.common.io import read_jsonl  # noqa: E402
from src.gateway.gateway import MAX_CALLS_SELECTIVE, for_record, run_always, run_oracle  # noqa: E402
from src.gateway.registry import REGISTRY  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "gateway_samples" / "gateway_log.jsonl"


def pick(records, record_id=None):
    if record_id:
        return next(r for r in records if r["record_id"] == record_id)
    return next(r for r in records if r["case_type"] == "T2" and r["gold"].get("required_checks"))


def bad_args(tool: str, args: dict) -> dict:
    """The first gold call with its resource argument under a wrong name."""
    param = REGISTRY[tool].resource_param
    wrong = "file" if param == "path" else "path"
    return {(wrong if k == param else k): v for k, v in args.items()}


def main(record_id=None) -> int:
    record = pick(read_jsonl(ROOT / "data" / "records" / "val.jsonl"), record_id)
    run_id = "gateway_sample"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("", encoding="utf-8")
    for setting in ("never", "always", "selective", "oracle"):
        gw = for_record(record, setting=setting, run_id=run_id)
        if setting == "always":
            run_always(gw)
        elif setting == "oracle":
            run_oracle(gw, record)
        elif setting == "selective":
            gold = record["gold"]["required_checks"]
            calls = [(gold[0]["tool"], bad_args(gold[0]["tool"], gold[0]["args"]))]
            calls += [(c["tool"], c["args"]) for c in gold]
            for tool, args in calls[:MAX_CALLS_SELECTIVE]:
                gw.call(tool, args)
        gw.write_log(OUT)
        print(f"{record['record_id']} {setting:9} {json.dumps(gw.summary())}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:2]))
