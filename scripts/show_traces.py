"""Reads a run's traces.jsonl (our records) and prints what the monitor did, record by record.

    python scripts/show_traces.py outputs/runs/<run_id> [--id IND-FIN-T1-001-B] [--wrong] [--prompt] [--summary]

Per record: the conversation's last user turn and the proposed action, the policies shown (and whether the gold
ones were among them), every pass (the model's raw answer), every gateway call with its result, and the final
decision next to gold. --wrong shows only records with the wrong decision; --prompt also prints the full prompt of
each pass; --summary prints only the counts (how often the model asked, for which checks, and with what result).
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.common.io import read_jsonl  # noqa: E402


def last_user_turn(prompt: str) -> str:
    convo = prompt.split("## Conversation", 1)[-1].split("## Proposed action", 1)[0]
    users = [line for line in convo.splitlines() if "] USER:" in line]
    return users[-1].strip() if users else ""


def proposed_action(prompt: str) -> str:
    return prompt.split("## Proposed action", 1)[-1].strip().splitlines()[0] if "## Proposed action" in prompt else ""


def show(t: dict, with_prompt: bool) -> None:
    g = t["gold"]
    mark = "OK " if t["correct"] else "BAD"
    first = t["passes"][0]["messages"][-1]["content"] if t["passes"] else ""
    print(f"\n{'=' * 100}\n[{mark}] {t['record_id']}  ({t['setting']}, {t['case_type']}"
          f"{' ' + (t['subtype'] or t['pair_side'] or '') if (t['subtype'] or t['pair_side']) else ''})")
    print(f"  user:   {last_user_turn(first)[:160]}")
    print(f"  action: {proposed_action(first)}")
    print(f"  policies shown (gold {'shown' if t['gold_policies_shown'] else 'NOT shown'}: {g['policy_ids']}):")
    for p in t["shown_policies"]:
        print(f"    [{p['ref']}] {p['policy_id']:10} {p['text'][:90]}")
    for i, p in enumerate(t["passes"], 1):
        if with_prompt:
            print(f"  --- prompt of pass {i} ---\n" + "\n".join("    " + line for line in p["messages"][-1]["content"].splitlines()))
        print(f"  pass {i} answer: {p['answer'].strip()[:400]}")
    for c in t["calls"]:
        print(f"  gateway: {c['tool']}({json.dumps(c['args'])}) -> {json.dumps(c['result'])[:200]}")
    out = t["output"] or {}
    print(f"  final:  {out.get('decision', 'INVALID')} / {out.get('risk_label', '-')} / {out.get('risk_type', '-')}"
          f"   gold: {g['decision']} / {g['risk_label']} / {g['risk_type']}")
    print(f"  gold check: needed={g['check_needed']} missing_fact={g['missing_fact']!r} required={g['required_checks']}")


def summary(traces: list[dict]) -> None:
    n = len(traces)
    asked = [t for t in traces if t["calls"]]
    needed = [t for t in traces if t["gold"]["check_needed"]]
    print(f"records {n} | correct decision {sum(t['correct'] for t in traces)} | invalid "
          f"{sum(t['output'] is None for t in traces)} | gold policies shown {sum(t['gold_policies_shown'] for t in traces)}")
    print(f"made a check: {len(asked)} | needed a check: {len(needed)} | needed and made: "
          f"{sum(bool(t['calls']) for t in needed)} | made but not needed: {sum(not t['gold']['check_needed'] for t in asked)}")
    print("checks asked:", dict(Counter(c["tool"] for t in traces for c in t["calls"]).most_common()))
    print("gateway errors:", dict(Counter(c["result"].get("error") for t in traces for c in t["calls"]
                                          if isinstance(c["result"], dict) and "error" in c["result"])))
    by = Counter((t["case_type"] + (t["subtype"] or ""), t["correct"]) for t in traces)
    print("correct by case:", {k: f"{by[(k, True)]}/{by[(k, True)] + by[(k, False)]}"
                               for k in sorted({k for k, _ in by})})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", help="outputs/runs/<run_id> (with traces.jsonl)")
    ap.add_argument("--id", help="only this record id")
    ap.add_argument("--wrong", action="store_true", help="only records with the wrong decision")
    ap.add_argument("--prompt", action="store_true", help="also print every prompt")
    ap.add_argument("--summary", action="store_true", help="only the counts")
    args = ap.parse_args(argv)
    traces = list(read_jsonl(Path(args.run) / "traces.jsonl"))
    if args.summary:
        summary(traces)
        return 0
    for t in traces:
        if (args.id and t["record_id"] != args.id) or (args.wrong and t["correct"]):
            continue
        show(t, args.prompt)
    print()
    summary(traces)
    return 0


if __name__ == "__main__":
    sys.exit(main())
