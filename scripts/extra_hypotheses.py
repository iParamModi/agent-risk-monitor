"""Exploratory hypotheses H2-H6 (decisions.md 2026-11-15), stated after the final results and written down before
this script was run. Every result is reported, whatever it gives. R10.4 is unchanged.

  H2 training teaches when to ask   records needing a check where the selective model makes >= 1 check of its own,
                                    Phase B - base: lower 95% bound > 0
  H3 checking helps                 accuracy Phase B selective - Phase B never: lower bound > 0
  H4 fine-tuning helps              accuracy Phase B selective - base selective: lower bound > 0
  H5 trust rule learned             H4 on T2 records only
  H6 no wasted checks               saving(selective) - saving(oracle), Phase B: lower bound >= -5 points

Final system v2. Judged with correct policies (as R10.4); retrieved policies shown for information.
Intervals: bootstrap by seed, 2,000 resamples, paired (src.eval.bootstrap).

    python scripts/extra_hypotheses.py      # -> docs/reports/extra_hypotheses.md
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.eval import metrics as m  # noqa: E402
from src.eval.bootstrap import _result, difference, paired_values  # noqa: E402
from src.eval.tables import table  # noqa: E402

spec = importlib.util.spec_from_file_location("final_results", ROOT / "scripts" / "final_results.py")
fr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fr)
fr.VERSION = "v2"

OUT = ROOT / "docs" / "reports" / "extra_hypotheses.md"
COND = {"gold": "correct", "retrieval": "retrieved"}


def ci(a, b, stat):
    return _result(stat(a, b), sorted(paired_values([a, b], stat)), 2000, 0.05)


def own_check(case: dict) -> bool:
    return any(not c.get("added_by") for c in case["calls"])


def ask_rate(cases):
    need = [c for c in cases if c["gold"]["check_needed"]]
    return sum(map(own_check, need)) / len(need) if need else None


def t2_accuracy(cases):
    t2 = [c for c in cases if c["case_type"] == "T2"]
    return m.accuracy(t2) if t2 else None


def saving_vs(always):
    n_always = sum(len(c["calls"]) for c in always)

    def stat(a, b):   # saving(a) - saving(b) = (calls(b) - calls(a)) / calls(always)
        return (sum(len(c["calls"]) for c in b) - sum(len(c["calls"]) for c in a)) / n_always
    return stat


def fmt(r, sign=True):
    f = (lambda x: f"{100 * x:+.1f}") if sign else (lambda x: f"{100 * x:.1f}")
    return f"{f(r['value'])} [{f(r['low'])}, {f(r['high'])}]"


def main() -> int:
    rows = []
    for split in ("test", "ood"):
        for cond, cname in COND.items():
            pb, base = fr.model_runs("phase_b", cond, split), fr.model_runs("base", cond, split)
            sel, bsel = pb["selective"], base["selective"]
            tests = [
                ("H2 training teaches when to ask", f"{100 * ask_rate(sel):.1f} vs {100 * ask_rate(bsel):.1f}",
                 ci(sel, bsel, difference(ask_rate)), 0.0, ">"),
                ("H3 checking helps", f"{100 * m.accuracy(sel):.1f} vs {100 * m.accuracy(pb['never']):.1f}",
                 ci(sel, pb["never"], difference(m.accuracy)), 0.0, ">"),
                ("H4 fine-tuning helps", f"{100 * m.accuracy(sel):.1f} vs {100 * m.accuracy(bsel):.1f}",
                 ci(sel, bsel, difference(m.accuracy)), 0.0, ">"),
                ("H5 trust rule learned (T2)", f"{100 * t2_accuracy(sel):.1f} vs {100 * t2_accuracy(bsel):.1f}",
                 ci(sel, bsel, difference(t2_accuracy)), 0.0, ">"),
                ("H6 no wasted checks", "", ci(sel, pb["oracle"], saving_vs(pb["always"])), -0.05, ">="),
            ]
            for name, values, r, bound, op in tests:
                ok = r["low"] > bound if op == ">" else r["low"] >= bound
                verdict = "**holds**" if ok else "not shown"
                if cond == "retrieval":
                    verdict += " (information)"
                rows.append([name, split, cname, values, fmt(r), verdict])
    rows.sort(key=lambda r: (r[0], r[1] != "test", r[2] != "correct"))
    md = ["# Exploratory hypotheses H2-H6", "",
          "**Exploratory.** Stated on 15 Nov 2026 after the final results were seen, and written in `docs/decisions.md` "
          "before this script was run; every result is reported. Judged with correct policies (as R10.4); rows with "
          "retrieved policies are for information. Final system v2; values in % (Phase B vs the comparison); difference "
          "in points with a 95% interval by bootstrap over seeds (2,000 resamples, paired). Built by "
          "`scripts/extra_hypotheses.py`.", "",
          "| | Hypothesis | Holds if |", "|---|---|---|",
          "| H2 | Training teaches when to ask | records needing a check where the selective model makes ≥ 1 check: Phase B − base, lower bound > 0 |",
          "| H3 | Checking helps | accuracy Phase B selective − Phase B never, lower bound > 0 |",
          "| H4 | Fine-tuning helps | accuracy Phase B selective − base selective, lower bound > 0 |",
          "| H5 | The trust rule is learned | H4 on T2 records only |",
          "| H6 | No wasted checks | saving(selective) − saving(oracle), lower bound ≥ −5 points |", "",
          *table(["Hypothesis", "Split", "Policies", "Values", "Difference [95% CI]", "Result"], rows), ""]
    OUT.write_text("\n".join(md), encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
