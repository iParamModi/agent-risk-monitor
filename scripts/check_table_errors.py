"""Runs every check the always setting makes (configs/check_table.yaml) and every gold required check (the
oracle setting) through the gateway, on all our decide_action records, and lists the calls that come back as an
error. A real company system answers these checks, so none of them should fail: an error here is either a gap in
a record's state (a user, contact or file the action names is missing) or a table row that does not fit the
action (e.g. a file check on a system). The always setting would otherwise see an error the other settings never
get.

    python scripts/check_table_errors.py            # exit 1 if any call fails

Reads only record states and actions (no training, no tuning), so the locked test and OOD records are included.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.common.io import read_jsonl  # noqa: E402
from src.gateway.gateway import _requested_by, for_record, table_calls  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FILES = ("all_in_domain.jsonl", "all_ood.jsonl")


def errors(records) -> dict[tuple, list[str]]:
    """(setting, tool, args, error, message) -> record ids."""
    out = defaultdict(list)
    for r in records:
        if r.get("task") != "decide_action":
            continue
        gw = for_record(r, "always", verify=False)
        current = _requested_by(r["seed_id"], r["set"])
        calls = [("always", t, a) for t, a in table_calls(r["visible"]["proposed_action"], current)]
        calls += [("oracle", c["tool"], c["args"]) for c in r["gold"].get("required_checks") or []]
        for setting, tool, args in calls:
            res = gw.call_result(tool, args)
            if res.status == "error":
                key = (setting, tool, json.dumps(args, sort_keys=True), res.error_code, res.message)
                out[key].append(f"{r['record_id']} ({r['split']})")
    return out


def main() -> int:
    records = [r for f in FILES for r in read_jsonl(ROOT / "data" / "records" / f)]
    found = errors(records)
    for (setting, tool, args, code, message), ids in sorted(found.items()):
        print(f"{setting:6} {code:13} {tool}({args}): {message}\n         {', '.join(ids)}")
    n = sum(len(v) for v in found.values())
    print(f"\n{len(records)} records, {n} failing calls in {len({i.split()[0] for v in found.values() for i in v})} records")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
