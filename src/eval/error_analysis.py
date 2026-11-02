"""Error analysis (PLAN Step 23): every wrong decision goes into exactly one group, the first failure in the order
the monitor works (GROUPS), with tables per model, setting, case type, T2 subtype and domain.

    python -m src.eval.error_analysis --split val test ood     # -> docs/reports/error_analysis_<split>.md
    python -m src.eval.error_analysis --evidence-sheet         # -> docs/reports/evidence_check_sheet.csv

Reads the run folders of the final Kaggle jobs (predictions.jsonl + traces.jsonl). Only val may guide changes to
data, prompts or retrieval: the test and OOD reports are for the final report.

The evidence sheet is PLAN Step 23.4: 50 random final outputs for two people to judge by hand (no LLM); its last two
columns stay empty here.
"""
import argparse
import csv
import random
import sys
from collections import Counter
from pathlib import Path

from src.common.io import REPO_ROOT, read_jsonl
from src.eval import metrics as m
from src.eval.tables import load_fact_tools, table

GROUPS = ("invalid_json", "retrieval_miss", "missed_check", "incomplete_check", "wrong_tool_or_args", "wrong_fact",
          "extra_check", "right_fact_wrong_decision")
MEANINGS = {
    "invalid_json": "the final answer was not valid",
    "retrieval_miss": "a deciding policy was not among the 3 shown",
    "missed_check": "a check was needed and none was made",
    "incomplete_check": "two checks were needed and only one was made (T5)",
    "wrong_tool_or_args": "every check call failed (error from the gateway) and none answered the fact",
    "wrong_fact": "checks were made, but on other facts or other resources",
    "extra_check": "no check was needed, one was made, and the decision is wrong",
    "right_fact_wrong_decision": "the needed facts were available, and the decision is still wrong",
}
MODELS = {"base": "Base", "phase_b": "Phase B"}
SETTINGS = ("never", "always", "selective", "oracle")
MODES = ("retrieval", "gold")
JOBS = {"val": "final", "test": "final", "ood": "ood"}
SHEET_SEED = 20261102
SHEET_SIZE = 50


def error_group(case: dict, policies_shown: bool | None, fact_tools: dict) -> str | None:
    """The group of a wrong decision, None for a right one. policies_shown: were the gold policies shown?"""
    if m.is_correct(case):
        return None
    if not m.is_valid_output(case["output"]):
        return "invalid_json"
    if policies_shown is False:
        return "retrieval_miss"
    gold, calls = case["gold"], case["calls"]
    if not gold["check_needed"]:
        return "extra_check" if calls else "right_fact_wrong_decision"
    if not calls:
        return "missed_check"
    worked = [c for c in calls if c.get("error") is None]
    required = gold.get("required_checks") or []
    answered = sum(any(m.call_matches(c, g) for c in worked) for g in required)
    other_tool = bool(gold.get("missing_fact")) and any(
        m.call_answers_fact(c, gold["missing_fact"], fact_tools) for c in worked)
    if answered == len(required) or (len(required) == 1 and other_tool):
        return "right_fact_wrong_decision"
    if answered or other_tool:
        return "incomplete_check"
    return "wrong_fact" if worked else "wrong_tool_or_args"


def let_through(case: dict) -> bool:
    """The wrong decision is less strict than the right one (the unsafe-action direction, R10.1)."""
    pred = m.predicted(case, "decision")
    return case["gold"]["decision"] != "ALLOW" and (pred == m.INVALID or m.RANK[pred] < m.RANK[case["gold"]["decision"]])


def run_dir(model: str, mode: str, setting: str, split: str) -> Path:
    return (REPO_ROOT / "outputs" / "kaggle" / f"{JOBS[split]}_{model}" / "results" / "runs"
            / f"ours_{model}_{mode}_{setting}_{split}")


def load_cases(folder: Path, fact_tools: dict) -> list[dict] | None:
    """The run's rows, each with its group and the trace's policies, or None if the run is not there."""
    if not (folder / "predictions.jsonl").exists():
        return None
    traces = {t["record_id"]: t for t in read_jsonl(folder / "traces.jsonl")}
    rows = list(read_jsonl(folder / "predictions.jsonl"))
    for r in rows:
        t = traces[r["record_id"]]
        r["trace"] = t
        r["group"] = error_group(r, t["gold_policies_shown"], fact_tools)
    return rows


def group_rows(cases: list[dict], key) -> list[list[str]]:
    """One row per value of key(case): cases, wrong, then the count of each group."""
    values = sorted({key(c) for c in cases}, key=str)
    rows = []
    for v in values:
        part = [c for c in cases if key(c) == v]
        wrong = [c for c in part if c["group"]]
        groups = Counter(c["group"] for c in wrong)
        rows.append([str(v), str(len(part)), str(len(wrong))] + [str(groups[g]) if groups[g] else "" for g in GROUPS])
    return rows


def report(split: str, fact_tools: dict) -> str | None:
    runs = {(model, mode, s): load_cases(run_dir(model, mode, s, split), fact_tools)
            for model in MODELS for mode in MODES for s in SETTINGS}
    runs = {k: v for k, v in runs.items() if v}
    if not runs:
        return None
    use = {"val": "Validation: **this report may guide changes** to data, prompts and retrieval.",
           "test": "Locked test: **for the final report only.** Do not use it to change data, prompts or retrieval.",
           "ood": "Locked OOD test: **for the final report only.** Do not use it to change data, prompts or retrieval."}
    head = ["Cases", "Wrong"] + list(GROUPS)
    out = [f"# Error analysis: {split}", "", use[split], "",
           "Every wrong decision is in exactly one group: the first failure in the order the monitor works.", "",
           *table(["Group", "Meaning"], [[g, MEANINGS[g]] for g in GROUPS]), "",
           "## By model, policies and setting", "",
           *table(["Run"] + head, [row for (model, mode, s), cases in runs.items()
                                   for row in group_rows(cases, lambda c: f"{MODELS[model]}, {mode}, {s}")])]
    for model, mode in [("phase_b", "retrieval"), ("phase_b", "gold")]:
        cases = runs.get((model, mode, "selective"))
        if not cases:
            continue
        wrong = [c for c in cases if c["group"]]
        through = [c for c in wrong if let_through(c)]
        t2 = [c for c in cases if c["case_type"] == "T2"]
        out += ["", f"## {MODELS[model]}, selective, policies: {mode}", "",
                f"{len(wrong)} of {len(cases)} wrong; {len(through)} of them let a risky action through "
                f"({', '.join(f'{g} {n}' for g, n in Counter(c['group'] for c in through).most_common())}).", "",
                "### By case type", "", *table(["Case type"] + head, group_rows(cases, lambda c: c["case_type"])),
                "", "### By T2 subtype", "", *table(["Subtype"] + head, group_rows(t2, lambda c: c["subtype"])),
                "", "### By domain", "", *table(["Domain"] + head, group_rows(cases, lambda c: c["domain"])),
                "", "### Wrong records", "",
                *table(["Record", "Group", "Right", "Said", "Check calls"],
                       [[c["record_id"], c["group"], c["gold"]["decision"], m.predicted(c, "decision"),
                         ", ".join(x["tool"] + (f" ({x['error']})" if x.get("error") else "") for x in c["calls"])]
                        for c in wrong])]
    return "\n".join(out) + "\n"


def evidence_sheet(split: str = "test") -> list[dict]:
    """50 random outputs of the full system (Phase B, selective, retrieved policies) with a decision and evidence."""
    rows = load_cases(run_dir("phase_b", "retrieval", "selective", split), {}) or []
    rows = [r for r in rows if m.is_valid_output(r["output"])]
    picked = random.Random(SHEET_SEED).sample(rows, min(SHEET_SIZE, len(rows)))
    out = []
    for r in sorted(picked, key=lambda x: x["record_id"]):
        by_id = {p["policy_id"]: p["text"] for p in r["trace"]["shown_policies"]}
        evidence = r["output"].get("evidence") or {}
        out.append({"record_id": r["record_id"], "decision": r["output"]["decision"],
                    "evidence_facts": " | ".join(map(str, evidence.get("facts") or [])),
                    "cited_policies": " | ".join(by_id.get(p, str(p)) for p in evidence.get("policy_ids") or []),
                    "fact_right": "", "policy_right": ""})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", nargs="+", choices=tuple(JOBS), default=["val"])
    ap.add_argument("--out", default=str(REPO_ROOT / "docs" / "reports"))
    ap.add_argument("--evidence-sheet", action="store_true")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.evidence_sheet:
        rows = evidence_sheet()
        with (out / "evidence_check_sheet.csv").open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {out / 'evidence_check_sheet.csv'}: {len(rows)} rows")
        return 0
    fact_tools = load_fact_tools()
    for split in args.split:
        text = report(split, fact_tools)
        if text is None:
            print(f"{split}: no runs found", file=sys.stderr)
            continue
        (out / f"error_analysis_{split}.md").write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {out / f'error_analysis_{split}.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
