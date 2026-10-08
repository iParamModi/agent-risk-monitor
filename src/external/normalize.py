"""Converts external records into our record format (DATASET.md section 2.4).

Run: python -m src.external.normalize
Writes data/external/r_judge.jsonl and data/external/atbench.jsonl (for code), plus one
readable <record_id>.json per record in data/external/r_judge/ and data/external/atbench/. Every record is
checked against configs/schemas/record.schema.json; failures are logged and skipped.
split and risk_type (for UNSAFE) stay null here: sample.py and map_risk.py fill them.
"""
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

from src.common.io import REPO_ROOT, write_json, write_jsonl, write_record_files
from src.common.schema import schema_errors
from src.external.load_atbench import load_atbench
from src.external.load_rjudge import load_rjudge

OUT_DIR = REPO_ROOT / "data" / "external"
REPORT = REPO_ROOT / "data" / "generated" / "reports" / "normalize_external.json"
TOOL_DESC_MAX = 200
TAXONOMY_KEYS = ("risk_source", "failure_mode", "real_world_harm")


def clean(text: str | None) -> str:
    """NFC, strip trailing spaces per line, collapse 3+ blank lines. Wording is never changed."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def message(role: str, text: str | None, tool_call: dict | None = None, action_text: str | None = None) -> dict:
    return {"role": role, "text": clean(text), "tool_call": tool_call, "action_text": action_text}


def parse_atbench_action(action: str) -> tuple[dict | None, str | None]:
    """JSON {"name", "arguments"} -> (tool_call, None). Anything else, e.g. Complete{...} -> (None, text)."""
    try:
        obj = json.loads(action)
        args = obj["arguments"]
        if isinstance(args, str):  # 6 records store arguments as a JSON string
            args = json.loads(args)
        if isinstance(obj.get("name"), str) and obj["name"] and isinstance(args, dict):
            return {"name": obj["name"], "args": args}, None
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
        pass
    return None, clean(action)


def external_record(*, record_id: str, seed_id: str, source: str, trajectory: list[dict], label: int,
                    source_note: str | None, source_taxonomy: dict | None, meta: dict) -> dict:
    risk_label = "UNSAFE" if label == 1 else "SAFE"
    return {
        "record_id": record_id, "seed_id": seed_id, "source": source, "set": "external", "split": None,
        "domain": None, "case_type": None, "subtype": None, "pair_side": None, "version": None,
        "task": "judge_trajectory",
        "visible": {"trajectory": trajectory, "proposed_action": None},
        "hidden": None,
        "gold": {
            "decision": None, "risk_label": risk_label,
            "risk_type": "NONE" if risk_label == "SAFE" else None,
            "risk_cause": None, "check_needed": None, "required_checks": None, "missing_fact": None,
            "policy_ids": None, "evidence": None,
            "source_note": clean(source_note) or None,
            "source_taxonomy": source_taxonomy if risk_label == "UNSAFE" else None,
        },
        "meta": {"writer_llm": None, "generator_version": None, "n_tokens": None, "ood_shift": [], **meta},
    }


def normalize_rjudge(rel_path: str, raw: dict) -> dict:
    """rel_path is like 'Program/security.json'. goal is dropped (same text in every record)."""
    stem, category = Path(rel_path).stem, rel_path.split("/")[0]
    trajectory = [message("context", raw["profile"])]
    for turn in (t for rnd in raw["contents"] for t in rnd):
        role = turn["role"]
        if role == "user":
            trajectory.append(message("user", turn["content"]))
        elif role == "agent":
            action = turn.get("action")
            trajectory.append(message("agent", turn.get("thought"),
                                      action_text=clean(action) if action is not None else None))
        elif role == "environment":
            if turn.get("content") is not None:
                trajectory.append(message("tool", turn["content"]))
        else:
            raise ValueError(f"unknown R-Judge role {role!r}")
    return external_record(
        record_id=f"RJ-{stem}-{raw['id']}", seed_id=f"RJ-scn-{stem}", source="r_judge",
        trajectory=trajectory, label=raw["label"], source_note=raw.get("risk_description"),
        source_taxonomy=None,
        meta={"category": category, "attack_type": raw.get("attack_type"),
              "source_file": rel_path, "source_id": raw["id"]})


def atbench_group(raw: dict) -> str:
    """Split unit: sha1 of the sorted tool names (DATASET.md section 2.2)."""
    names = sorted(t["name"] for t in raw["tool_used"])
    return "ATB-grp-" + hashlib.sha1("|".join(names).encode("utf-8")).hexdigest()[:8]


def normalize_atbench(raw: dict) -> dict:
    tool_lines = []
    for tool in raw["tool_used"]:
        first_line = clean(tool.get("description")).split("\n")[0][:TOOL_DESC_MAX]
        tool_lines.append(f"- {tool['name']}: {first_line}" if first_line else f"- {tool['name']}")
    trajectory = [message("context", "Available tools:\n" + "\n".join(tool_lines))]
    for rnd in raw["contents"]:
        for turn in rnd:
            role = turn["role"]
            if role == "user":
                trajectory.append(message("user", turn["content"]))
            elif role == "agent":
                tool_call, action_text = parse_atbench_action(turn["action"])
                trajectory.append(message("agent", turn.get("thought"), tool_call, action_text))
            elif role == "environment":
                trajectory.append(message("tool", turn["content"]))
            else:
                raise ValueError(f"unknown ATBench role {role!r}")
    return external_record(
        record_id=f"ATB-{raw['id']}", seed_id=atbench_group(raw), source="atbench",
        trajectory=trajectory, label=raw["label"], source_note=raw.get("reason"),
        source_taxonomy={k: raw[k] for k in TAXONOMY_KEYS},
        meta={"category": None, "attack_type": None,
              "source_file": "ATBench/test.json", "source_id": raw["id"]})


def run(items, convert, name: str) -> tuple[list[dict], dict]:
    good, failures = [], []
    for item in items:
        args = item if isinstance(item, tuple) else (item,)
        try:
            rec = convert(*args)
        except Exception as e:  # logged and skipped, never silently fixed
            failures.append({"raw": str(args[-1].get("id")), "errors": [f"{type(e).__name__}: {e}"]})
            continue
        errors = schema_errors(rec)
        if errors:
            failures.append({"record_id": rec["record_id"], "errors": errors})
        else:
            good.append(rec)
    ids = Counter(r["record_id"] for r in good)
    dupes = [i for i, n in ids.items() if n > 1]
    if dupes:
        raise ValueError(f"{name}: duplicate record_ids {dupes[:5]}")
    labels = Counter(r["gold"]["risk_label"] for r in good)
    stats = {"records": len(good), "failed": len(failures), "safe": labels["SAFE"], "unsafe": labels["UNSAFE"],
             "seed_groups": len({r["seed_id"] for r in good}), "failures": failures}
    return good, stats


def main() -> int:
    rjudge, rj_stats = run(load_rjudge(), normalize_rjudge, "r_judge")
    atbench, atb_stats = run(load_atbench(), normalize_atbench, "atbench")
    for name, records in (("r_judge", rjudge), ("atbench", atbench)):
        write_jsonl(OUT_DIR / f"{name}.jsonl", records)
        write_record_files(OUT_DIR / name, records)
    write_json(REPORT, {"r_judge": rj_stats, "atbench": atb_stats})
    for name, s in (("r_judge", rj_stats), ("atbench", atb_stats)):
        print(f"{name}: {s['records']} records ({s['safe']} safe / {s['unsafe']} unsafe), "
              f"{s['seed_groups']} groups, {s['failed']} failed")
    return 1 if rj_stats["failed"] or atb_stats["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
