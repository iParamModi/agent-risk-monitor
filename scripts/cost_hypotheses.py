"""Cost hypotheses: does selective checking keep (almost) the accuracy of always checking at a fraction of the cost?

Exploratory, stated on 12 Nov 2026 AFTER the final results were seen (decisions.md 2026-11-12). R10.4 (safety) stays
the only hypothesis fixed before any result. To keep these from being fitted to the numbers, the thresholds are
round values fixed in advance of running this script, and the margin is the same 5 points as R10.4:

  C1 fewer checks       selective makes at most half the check calls of always:
                        upper 95% bound of checks(selective) / checks(always) <= 0.5
  C2 lower compute      selective uses at most half the tokens (prompt + output) per record of always:
                        upper 95% bound of tokens(selective) / tokens(always) <= 0.5
  C3 accuracy kept      selective is at most 5 points less accurate than always (non-inferiority):
                        lower 95% bound of accuracy(selective) - accuracy(always) >= -5 points
  C4 beats fixed rules  Phase B selective is more accurate than rules + environment (rules that run every check):
                        lower 95% bound of accuracy(Phase B selective) - accuracy(rules + environment) > 0

Plus, as description only: cost per correct decision, and the share of always's accuracy gain over never that
selective keeps. Intervals: bootstrap by seed, 2,000 resamples, paired (src.eval.bootstrap, as R10.4).
Runs: the same folders as scripts/final_results.py, for v1 and v2.

    python scripts/cost_hypotheses.py      # -> docs/reports/cost_hypotheses.md
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.eval import metrics as m  # noqa: E402
from src.eval.bootstrap import _result, difference, paired_values  # noqa: E402
from src.eval.tables import pct, table  # noqa: E402

spec = importlib.util.spec_from_file_location("final_results", ROOT / "scripts" / "final_results.py")
fr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fr)

OUT = ROOT / "docs" / "reports" / "cost_hypotheses.md"
SPLITS = ("test", "ood", "val")
COND = {"retrieval": "retrieved", "gold": "correct"}
MAX_RATIO = 0.5
MARGIN = 0.05


def tokens(case: dict) -> float | None:
    if case.get("tokens_in") is None:
        return None
    return case["tokens_in"] + (case.get("tokens_out") or 0)


def mean_of(key):
    def stat(cases: list[dict]) -> float | None:
        vals = [v for v in map(key, cases) if v is not None]
        return sum(vals) / len(vals) if vals else None
    return stat


def calls(case: dict) -> float:
    return float(len(case["calls"]))


def ratio(metric):
    def stat(a: list[dict], b: list[dict]) -> float | None:
        va, vb = metric(a), metric(b)
        return None if va is None or not vb else va / vb
    return stat


def ci(a: list[dict], b: list[dict], stat) -> dict:
    return _result(stat(a, b), sorted(paired_values([a, b], stat)), 2000, 0.05)


def fmt(r: dict, scale: float = 100, digits: int = 1, sign: bool = False) -> str:
    f = (lambda x: f"{scale * x:+.{digits}f}") if sign else (lambda x: f"{scale * x:.{digits}f}")
    return f"{f(r['value'])} [{f(r['low'])}, {f(r['high'])}]"


def verdict(ok: bool) -> str:
    return "**holds**" if ok else "does not hold"


def runs(version: str, model: str, cond: str, split: str):
    fr.VERSION = version
    return fr.baseline_runs(cond, split) if model == "rules" else fr.model_runs(model, cond, split)


def main() -> int:
    acc, chk, tok = m.accuracy, mean_of(calls), mean_of(tokens)
    rows_c, rows_acc, rows_rules, rows_desc = [], [], [], []
    for split in SPLITS:
        for cond in COND:
            for v in ("v1", "v2"):
                pb, rules = runs(v, "phase_b", cond, split), runs(v, "rules", cond, split)
                if not pb:
                    continue
                sel, alw, nev = pb["selective"], pb["always"], pb["never"]
                label = [split, COND[cond], v]
                c1, c2 = ci(sel, alw, ratio(chk)), ci(sel, alw, ratio(tok))
                rows_c.append([*label, f"{chk(sel):.2f} vs {chk(alw):.2f}", fmt(c1, 1, 2), verdict(c1["high"] <= MAX_RATIO),
                               f"{tok(sel):,.0f} vs {tok(alw):,.0f}", fmt(c2, 1, 2), verdict(c2["high"] <= MAX_RATIO)])
                c3 = ci(sel, alw, difference(acc))
                rows_acc.append([*label, pct(acc(sel)), pct(acc(alw)), fmt(c3, sign=True), verdict(c3["low"] >= -MARGIN)])
                if rules:
                    c4 = ci(sel, rules["always"], difference(acc))
                    rows_rules.append([*label, pct(acc(sel)), pct(acc(rules["always"])), fmt(c4, sign=True),
                                       f"{chk(sel):.2f} vs {chk(rules['always']):.2f}", verdict(c4["low"] > 0)])
                gain = acc(alw) - acc(nev)
                kept = f"{100 * (acc(sel) - acc(nev)) / gain:.0f}%" if gain > 0 else "– (always not above never)"
                per_right = {s: tok(pb[s]) * len(pb[s]) / max(1, sum(map(m.is_correct, pb[s]))) for s in ("selective", "always")}
                breakeven = (tok(sel) - tok(alw)) / (chk(alw) - chk(sel))
                rows_desc.append([*label, kept, f"{100 * chk(sel) / chk(alw):.0f}%",
                                  f"{mean_of(lambda c: c.get('passes'))(sel):.2f}", f"{breakeven:,.0f}",
                                  f"{per_right['selective']:,.0f} vs {per_right['always']:,.0f}",
                                  f"{mean_of(lambda c: c.get('time_s'))(sel):.1f} vs {mean_of(lambda c: c.get('time_s'))(alw):.1f}"])
    md = ["# Cost hypotheses: almost the same accuracy for less checking?", "",
          "**Exploratory.** Stated on 12 Nov 2026, after the final results were seen; the safety hypothesis R10.4 "
          "(`final_report_results.md` section 4) stays the only one fixed before any result. The thresholds below are round "
          "values (half the cost; the same 5-point margin as R10.4), not chosen from these numbers. Phase B adapter (final), "
          "selective vs always on the same records; 95% intervals by bootstrap over seeds (2,000 resamples, paired). "
          "v2 = the final system (tag-filtered retrieval, 8 policies, second-source check); with correct policies only "
          "selective differs between v1 and v2. Built by `scripts/cost_hypotheses.py` from the finished runs.", "",
          "| | Hypothesis | Holds if |", "|---|---|---|",
          "| C1 | Selective needs far fewer checks than always | upper bound of checks(selective) / checks(always) ≤ 0.5 |",
          "| C2 | Selective needs far less model compute than always | upper bound of tokens(selective) / tokens(always) ≤ 0.5 |",
          "| C3 | Selective keeps the accuracy of always (non-inferiority) | lower bound of accuracy(selective) − accuracy(always) ≥ −5 points |",
          "| C4 | Phase B selective beats rules that run every check | lower bound of accuracy(Phase B selective) − accuracy(rules + environment) > 0 |", "",
          "## C1, C2: cost", "",
          "Checks = check-tool calls per record; tokens = prompt + output tokens per record, summed over the model's passes "
          "(the always prompt carries every check result).", "",
          *table(["Split", "Policies", "System", "Checks / record (sel vs always)", "Ratio [95% CI]", "C1",
                  "Tokens / record (sel vs always)", "Ratio [95% CI]", "C2"], rows_c), "",
          "## C3: accuracy kept", "",
          *table(["Split", "Policies", "System", "Selective", "Always", "Δ accuracy [95% CI]", "C3"], rows_acc), "",
          "## C4: against rules that run every check", "",
          *table(["Split", "Policies", "System", "Phase B selective", "Rules + environment", "Δ accuracy [95% CI]",
                  "Checks / record", "C4"], rows_rules), "",
          "## Description: what the cost buys", "",
          "Gain kept = (selective − never) / (always − never) accuracy: the share of what always checking adds over no checks "
          "that selective keeps. Tokens per correct decision = all tokens of the run / records decided right.", "",
          *table(["Split", "Policies", "System", "Gain kept", "Checks used (% of always)", "Model passes / record (sel)",
                  "Break-even tokens per check", "Tokens per correct decision (sel vs always)",
                  "Seconds / record (sel vs always)"], rows_desc), "",
          "## What this means", "",
          "- **Fewer check calls: yes (C1).** Selective makes 14-17% of always's check calls on every split, system and "
          "policy condition.",
          "- **Less model compute: no (C2).** Selective uses about 2.4 times the tokens of always and takes about twice as "
          "long per record. Two reasons: its prompt lists every check tool (about 1,000 tokens more than the always prompt, "
          "which only carries the results), and most records need a second pass after the checks (1.6-1.8 passes per record; "
          "always and never make one). Selective is therefore cheaper overall only where a check call costs more than about "
          "the break-even column (310-410 tokens of model compute per call; 382 on test, v2): real company APIs with latency, rate "
          "limits, fees or exposure of personal data, not a free local lookup. Showing only the action's check tools (v3, "
          "not run) and reusing the shared prompt prefix between the two passes are the obvious ways to cut this.",
          "- **Same accuracy: not shown on test (C3).** Selective with retrieved policies is level with always under v2 "
          "(+0.7), but the interval [−7.7, +8.6] is too wide for a 5-point non-inferiority claim; with correct policies it "
          "is 5.5 points behind. On OOD with correct policies selective is clearly **more** accurate than always "
          "(+14.3 [3.4, 25.0]).",
          "- **Better than rules that check everything (C4), at about one sixth of the checks:** holds on test (v2, both "
          "policy conditions) and on OOD with correct policies; val is too small (40 records) to show it.",
          "- Gain kept is unstable where always and never are close (it can exceed 100% or be undefined): read it with the "
          "accuracies above.", ""]
    OUT.write_text("\n".join(md), encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
