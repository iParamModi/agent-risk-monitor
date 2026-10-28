"""The 30 Oct results report: for val and test and both policy conditions, the rule baselines next to base Qwen3-8B
and the Phase B adapter in the 4 settings, with the main metrics (decisions.md R10), 95% intervals and the
selective-vs-always tests per model. Built from the run folders of the final Kaggle jobs and src.baselines.run.

    python scripts/final_results.py      # -> docs/reports/final_results_30oct.md + .json

A model or baseline whose runs are missing is left out (and named at the top), so it can be run before every job
has finished. All metrics come from src.eval (src.eval.tables.build_report); nothing is computed differently here.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.common.io import read_jsonl, write_json  # noqa: E402
from src.eval.tables import build_report, num, p_value, pct, with_ci  # noqa: E402

SETTINGS = ("never", "always", "selective", "oracle")
MODELS = {"base": ("Base Qwen3-8B", "outputs/kaggle/final_base/results/runs"),
          "phase_b": ("Phase B (QLoRA)", "outputs/kaggle/final_phase_b/results/runs")}
BASELINES = {"never": "rules_only", "always": "rules_env"}
CONDITIONS = {"retrieval": "retrieved top 3 policies (the full system)",
              "gold": "gold policies + 2 look-alikes (retrieval assumed perfect)"}


def load(path: Path) -> list[dict] | None:
    return list(read_jsonl(path / "predictions.jsonl")) if (path / "predictions.jsonl").exists() else None


def model_runs(model: str, cond: str, split: str) -> dict[str, list[dict]] | None:
    runs = {s: load(ROOT / MODELS[model][1] / f"ours_{model}_{cond}_{s}_{split}") for s in SETTINGS}
    return runs if all(v is not None for v in runs.values()) else None


def baseline_runs(cond: str, split: str) -> dict[str, list[dict]] | None:
    runs = {s: load(ROOT / "outputs" / "runs" / f"{name}_{cond}_{split}") for s, name in BASELINES.items()}
    return runs if all(v is not None for v in runs.values()) else None


def row(label: str, setting: str, s: dict, saving) -> str:
    invalid = round(s["cases"] * (1 - (s.get("valid_json_rate") or 0)))
    return (f"| {label} | {setting} | {with_ci(s['ci']['accuracy'])} | {pct(s['unsafe_action_rate'])} | "
            f"{pct(s['wrong_block_rate'])} | {pct(s['decision_f1']['macro'])} | {num(s['checks_per_case'])} | "
            f"{pct(saving)} | {pct(s['check_precision'])} | {pct(s['check_recall'])} | "
            f"{pct(s['correct_missing_fact'])} | {invalid} |")


def section(split: str, cond: str, reports: dict, n_resamples: int) -> list[str]:
    head = ["| Method | Setting | Accuracy [95% CI] | Unsafe action | Wrong block | Decision macro-F1 | Checks / case | "
            "Saving vs always | Check precision | Check recall | Right missing fact | Invalid |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    lines = [f"### {split.capitalize()}, {CONDITIONS[cond]}", ""]
    rows, tests = [], []
    if "rules" in reports:
        r = reports["rules"]
        for s, name in BASELINES.items():
            label = "Rules only" if s == "never" else "Rules + environment"
            rows.append(row(label, s, r["settings"][s], r.get("saving", {}).get(s)))
    for model, (label, _) in MODELS.items():
        r = reports.get(model)
        if not r:
            continue
        for s in SETTINGS:
            rows.append(row(label, s, r["settings"][s], r["saving"].get(s)))
        h, t = r["hypothesis"], r["selective_vs_always"]
        acc = t["accuracy_diff"]
        tests.append(f"| {label} | {with_ci(h)} (margin {pct(h['margin'])}) | {'**passes**' if h['passes'] else 'fails'} | "
                     f"{with_ci(acc)} | {p_value(t['tests']['correct']['by_case']['p_value'])} | "
                     f"{num(t['tests']['checks']['by_case']['mean_a'])} vs {num(t['tests']['checks']['by_case']['mean_b'])} "
                     f"(p {p_value(t['tests']['checks']['by_case']['p_value'])}) |")
    n = next(iter(next(iter(reports.values()))["settings"].values()))["cases"]
    lines += [f"{n} records. Rates in %, accuracy with a 95% bootstrap interval over seeds ({n_resamples} resamples).",
              "", *head, *rows, ""]
    if tests:
        lines += ["**Selective vs always** (R10.4: selective is not less safe than always if the upper bound of "
                  "Δ unsafe-action rate (selective − always) is at most 5 points):", "",
                  "| Model | Δ unsafe action [95% CI] | Hypothesis | Δ accuracy [95% CI] | McNemar p (accuracy) | "
                  "Checks / case, selective vs always |", "|---|---|---|---|---|---|", *tests, ""]
    return lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "docs" / "reports" / "final_results_30oct"))
    ap.add_argument("--resamples", type=int, default=2000)
    args = ap.parse_args(argv)
    md = ["# Results for the 30 Oct submission: our val and test records", "",
          "Monitor: Qwen3-8B, base and with the Phase B QLoRA adapter, in 4 settings (never / always / selective / "
          "oracle), next to two rule baselines (rules only = never check, rules + environment = always check). "
          "Test is the locked in-domain test set (phase 1 records), run once with the final setup; nothing was tuned "
          "on it. Definitions: docs/evaluation_metrics.md; runs: kaggle/our_eval_final_*, src/baselines/run.py.", ""]
    missing, out = [], {}
    for split in ("val", "test"):
        md += [f"## {split.capitalize()}", ""]
        for cond in CONDITIONS:
            reports = {}
            b = baseline_runs(cond, split)
            if b:
                reports["rules"] = build_report(b, args.resamples)
            else:
                missing.append(f"rule baselines {cond} {split}")
            for model in MODELS:
                runs = model_runs(model, cond, split)
                if runs:
                    reports[model] = build_report(runs, args.resamples)
                else:
                    missing.append(f"{model} {cond} {split}")
            if reports:
                md += section(split, cond, reports, args.resamples)
                out[f"{split}_{cond}"] = reports
    if missing:
        md[2:2] = [f"**Not in this version (runs missing):** {', '.join(missing)}.", ""]
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out + ".md").write_text("\n".join(md), encoding="utf-8", newline="\n")
    write_json(Path(args.out + ".json"), out)
    print(f"wrote {args.out}.md and .json" + (f" (missing: {', '.join(missing)})" if missing else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
