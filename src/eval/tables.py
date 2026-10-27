"""Writes the results report: outputs/tables/main.md + main.json (decisions.md R10).

Run: python -m src.eval.tables --run never=outputs/runs/<id> --run always=... --run selective=... --run oracle=...
Each run folder holds predictions.jsonl (case rows, format in src/eval/metrics.py). All runs must
cover the same records. Settings may be missing; the hypothesis and paired tests need selective + always.
"""
import argparse
import sys
from pathlib import Path

import yaml

from src.common.io import REPO_ROOT, read_jsonl, write_json
from src.eval import metrics as m
from src.eval.bootstrap import N_RESAMPLES, bootstrap_ci, hypothesis_check, paired_diff_ci
from src.eval.stats_tests import compare

SETTINGS = ("never", "always", "selective", "oracle")
OUT_DIR = REPO_ROOT / "outputs" / "tables"
FACT_CHECKS = REPO_ROOT / "configs" / "fact_checks.yaml"
CI_METRICS = {     # main numbers that get a 95% interval
    "unsafe_action_rate": m.unsafe_action_rate,
    "wrong_block_rate": m.wrong_block_rate,
    "accuracy": m.accuracy,
    "checks_per_case": m.checks_per_case,
}


def load_run(folder: str | Path) -> list[dict]:
    return list(read_jsonl(Path(folder) / "predictions.jsonl"))


def load_fact_tools(path: Path = FACT_CHECKS) -> dict:
    """fact -> [{"tool", "resource_param"}] from configs/fact_checks.yaml ({} if it does not exist)."""
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {fact: [{"tool": t["tool"], "resource_param": t["resource_param"]} for t in tools]
            for fact, tools in raw.items()}


def build_report(runs: dict[str, list[dict]], n_resamples: int = N_RESAMPLES, fact_tools: dict | None = None) -> dict:
    ids = {name: sorted(c["record_id"] for c in cases) for name, cases in runs.items()}
    if len({tuple(v) for v in ids.values()}) > 1:
        raise ValueError("all runs must cover the same records")
    fact_tools = load_fact_tools() if fact_tools is None else fact_tools
    report = {"settings": {}, "n_resamples": n_resamples}
    for name, cases in runs.items():
        s = m.summary(cases, fact_tools)
        s["ci"] = {k: bootstrap_ci(cases, f, n=n_resamples) for k, f in CI_METRICS.items()}
        s["by_case_type"] = m.by_group(cases, "case_type")
        s["by_domain"] = m.by_group(cases, "domain")
        s["unsafe_by_case_type"] = m.by_group(cases, "case_type", m.unsafe_action_rate)
        report["settings"][name] = s
    if "always" in runs:
        always_calls = m.total_calls(runs["always"])
        report["saving"] = {name: m.saving(m.total_calls(c), always_calls) for name, c in runs.items()}
        report["oracle_saving"] = m.saving(m.oracle_calls(runs["always"]), always_calls)
    if "selective" in runs and "always" in runs:
        sel, alw = runs["selective"], runs["always"]
        report["hypothesis"] = hypothesis_check(sel, alw, n=n_resamples)
        report["selective_vs_always"] = {
            "tests": compare(sel, alw),
            "accuracy_diff": paired_diff_ci(sel, alw, m.accuracy, n=n_resamples),
            "checks_diff": paired_diff_ci(sel, alw, m.checks_per_case, n=n_resamples),
        }
    return report


# ---------- markdown ----------

def pct(x) -> str:
    return "–" if x is None else f"{100 * x:.1f}"


def num(x, digits=2) -> str:
    return "–" if x is None else f"{x:.{digits}f}"


def with_ci(r: dict, fmt=pct) -> str:
    return f"{fmt(r['value'])} [{fmt(r['low'])}, {fmt(r['high'])}]"


def p_value(p) -> str:
    return "–" if p is None else ("< 0.001" if p < 0.001 else f"{p:.3f}")


def table(header: list[str], rows: list[list[str]]) -> list[str]:
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(r) + " |" for r in rows]


def to_markdown(report: dict, title: str = "Results") -> str:
    st = report["settings"]
    names = [s for s in SETTINGS if s in st] + [s for s in st if s not in SETTINGS]
    out = [f"# {title}", "",
           f"Rates in %. Brackets: 95% bootstrap interval by seed ({report['n_resamples']} resamples).", ""]

    h = report.get("hypothesis")
    if h:
        verdict = "PASSES" if h["passes"] else "FAILS"
        out += ["## Hypothesis (R10.4)", "",
                f"Δ unsafe-action rate (selective − always) = **{with_ci(h)}** points. "
                f"Upper bound must be ≤ {pct(h['margin'])}: **{verdict}**.", ""]

    out += ["## Main metrics", ""]
    rows = []
    for n in names:
        s = st[n]
        rows.append([n, with_ci(s["ci"]["unsafe_action_rate"]), with_ci(s["ci"]["wrong_block_rate"]),
                     pct(s["extra_confirmation_rate"]), with_ci(s["ci"]["accuracy"]), pct(s["decision_f1"]["macro"]),
                     with_ci(s["ci"]["checks_per_case"], num), pct(report.get("saving", {}).get(n)),
                     pct(s["valid_json_rate"])])
    out += table(["Setting", "Unsafe-action", "Wrong-block", "Extra confirm", "Accuracy", "Decision macro-F1",
                  "Checks / case", "Saving vs always", "Valid JSON"], rows)
    if "oracle_saving" in report:
        out += ["", f"Oracle saving (best possible): **{pct(report['oracle_saving'])}**"]

    t = report.get("selective_vs_always")
    if t:
        c, k = t["tests"]["checks"], t["tests"]["correct"]
        out += ["", "## Selective vs always (paired)", ""]
        out += table(["Question", "Test", "Result", "p (per record)", "p (per seed)"], [
            ["Fewer checks?", "Wilcoxon", f"{num(c['by_case']['mean_a'])} vs {num(c['by_case']['mean_b'])} checks / case; "
             f"Δ {with_ci(t['checks_diff'], num)}", p_value(c["by_case"]["p_value"]), p_value(c["by_seed"]["p_value"])],
            ["Accuracy different?", "McNemar (exact)", f"only selective right {k['by_case']['only_a_right']}, "
             f"only always right {k['by_case']['only_b_right']}; Δ {with_ci(t['accuracy_diff'])}",
             p_value(k["by_case"]["p_value"]), p_value(k["by_seed"]["p_value"])],
        ])

    out += ["", "## Checks", ""]
    out += table(["Setting", "Precision", "Recall", "Correct missing fact", "Total calls"],
                 [[n, pct(st[n]["check_precision"]), pct(st[n]["check_recall"]), pct(st[n]["correct_missing_fact"]),
                   str(st[n]["total_calls"])] for n in names])

    out += ["", "## Decision F1 per class", ""]
    out += table(["Setting"] + list(m.DECISIONS),
                 [[n] + [pct(st[n]["decision_f1"]["per_class"][d]) for d in m.DECISIONS] for n in names])

    out += ["", "## Risk label and risk type", ""]
    out += table(["Setting", "Risk-label F1", "Risk-type macro-F1"] + list(m.RISK_TYPES),
                 [[n, pct(st[n]["risk_label_f1"]), pct(st[n]["risk_type_f1"]["macro"])]
                  + [pct(st[n]["risk_type_f1"]["per_class"][r]) for r in m.RISK_TYPES] for n in names])

    case_types = sorted({ct for n in names for ct in st[n]["by_case_type"]}, key=str)
    out += ["", "## Accuracy per case type (unsafe-action rate in brackets)", ""]
    out += table(["Setting"] + [str(ct) for ct in case_types] + ["T1 pair accuracy"],
                 [[n] + [f"{pct(st[n]['by_case_type'].get(ct))} ({pct(st[n]['unsafe_by_case_type'].get(ct))})"
                         for ct in case_types] + [pct(st[n]["pair_accuracy"])] for n in names])

    out += ["", "## T2 accuracy per subtype", ""]
    out += table(["Setting", "a", "b", "c", "d"], [[n] + [pct(st[n]["t2_accuracy"][s]) for s in "abcd"] for n in names])

    domains = sorted({d for n in names for d in st[n]["by_domain"]}, key=str)
    out += ["", "## Accuracy per domain", ""]
    out += table(["Setting"] + [str(d) for d in domains],
                 [[n] + [pct(st[n]["by_domain"].get(d)) for d in domains] for n in names])

    out += ["", "## Cost and tool use", ""]
    out += table(["Setting", "Passes", "Tokens in", "Tokens out", "Time (s)", "Correct tool name", "Valid args",
                  "Recovery after error", "Blocked writes"],
                 [[n, num(st[n]["costs"]["passes"]), num(st[n]["costs"]["tokens_in"], 0),
                   num(st[n]["costs"]["tokens_out"], 0), num(st[n]["costs"]["time_s"]),
                   pct(st[n]["call_quality"]["correct_tool_name"]), pct(st[n]["call_quality"]["valid_args"]),
                   pct(st[n]["call_quality"]["recovery_after_error"]),
                   str(st[n]["call_quality"]["blocked_write_attempts"])] for n in names])
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", action="append", required=True, metavar="SETTING=FOLDER")
    ap.add_argument("--out", default=str(OUT_DIR), help="folder for main.md and main.json")
    ap.add_argument("--name", default="main")
    ap.add_argument("--title", default="Results")
    ap.add_argument("--resamples", type=int, default=N_RESAMPLES)
    args = ap.parse_args(argv)
    runs = {}
    for item in args.run:
        setting, _, folder = item.partition("=")
        runs[setting] = load_run(folder)
    report = build_report(runs, args.resamples)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / f"{args.name}.json", report)
    (out / f"{args.name}.md").write_text(to_markdown(report, args.title), encoding="utf-8")
    print(f"wrote {out / args.name}.md and .json")
    if "hypothesis" in report:
        h = report["hypothesis"]
        print(f"hypothesis: delta {pct(h['value'])} [{pct(h['low'])}, {pct(h['high'])}] -> "
              f"{'PASSES' if h['passes'] else 'FAILS'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
