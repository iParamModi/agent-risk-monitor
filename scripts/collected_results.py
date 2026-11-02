"""Risk detection on the collected datasets: test next to val, for base Qwen3-8B, Phase A and Phase B.

    python scripts/collected_results.py      # -> docs/reports/collected_test_results.md

Built from the run folders of kaggle/collected_test (test) and kaggle/base_eval, lora_eval, finetune (val). Counts and
scores only; predictions stay local (AgentRisk has no licence). All metrics come from src.eval.metrics.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.common.io import read_jsonl  # noqa: E402
from src.eval import metrics as m  # noqa: E402
from src.eval.tables import pct, table  # noqa: E402

KAGGLE = ROOT / "outputs" / "kaggle"
MODELS = {"base": "Base", "phase_a": "Phase A", "phase_b": "Phase B"}
SOURCES = {"r_judge": "R-Judge", "atbench": "ATBench", "agentrisk": "AgentRisk"}
VAL_RUNS = {"base": "base_eval/results/runs/base_qwen3_8b_fp16_{}",
            "phase_a": "lora_eval/results/runs/lora_phase_a_qwen3_8b_{}",
            "phase_b": "finetune_phase_b/results/runs/lora_phase_b_qwen3_8b_{}"}


def load(split: str, model: str, source: str) -> list[dict]:
    folder = (KAGGLE / "collected_test/results/runs" / f"collected_{model}_{source}_test" if split == "test"
              else KAGGLE / VAL_RUNS[model].format(source))
    return list(read_jsonl(folder / "predictions.jsonl"))


def label_accuracy(cases: list[dict]) -> float:
    return m.rate(sum(m.predicted(c, "risk_label") == c["gold"]["risk_label"] for c in cases), len(cases))


def caught(cases: list[dict], label: str) -> tuple[int, int]:
    """(cases of this gold label that the model calls UNSAFE, cases of this gold label)."""
    part = [c for c in cases if c["gold"]["risk_label"] == label]
    return sum(m.predicted(c, "risk_label") == "UNSAFE" for c in part), len(part)


def rows_for(split: str) -> list[list[str]]:
    rows = []
    for model, label in MODELS.items():
        per = {s: load(split, model, s) for s in SOURCES}
        for source, cases in [*per.items(), ("all", [c for v in per.values() for c in v])]:
            unsafe, safe = caught(cases, "UNSAFE"), caught(cases, "SAFE")
            rows.append([label, SOURCES.get(source, "**All**"), str(len(cases)), pct(label_accuracy(cases)),
                         pct(m.risk_label_f1(cases)), pct(m.risk_type_f1(cases)["macro"]),
                         f"{unsafe[0]} of {unsafe[1]}", f"{safe[0]} of {safe[1]}", pct(m.valid_json_rate(cases))])
    return rows


def main() -> int:
    notes = json.loads((KAGGLE / "collected_test/results/notes.json").read_text(encoding="utf-8"))
    skipped = notes["skipped_long"]
    head = ["Model", "Source", "Records", "Safe/unsafe accuracy", "Risk-label F1", "Risk-type macro-F1",
            "Unsafe caught", "Safe flagged unsafe", "Valid JSON"]
    md = ["# Risk detection on the collected datasets: test and val", "",
          "Setting `never` (one pass, risk answer only), float16, greedy, Kaggle T4 x2. Scoring only: nothing was trained "
          "or tuned on these test records. These numbers come from **our own splits**, so they cannot be compared with "
          "published leaderboards (PLAN Step 25.5). Base = no training; Phase A = trained on collected data only; "
          "Phase B = trained on collected and generated data.", "",
          f"{len(skipped)} test records over {notes['max_tokens']} tokens are left out, as on val "
          f"({sum(s['label'] == 'UNSAFE' for s in skipped)} of them UNSAFE, all ATBench).", "",
          "## Test", "", *table(head, rows_for("test")), "", "## Val (for comparison)", "", *table(head, rows_for("val")), ""]
    out = ROOT / "docs" / "reports" / "collected_test_results.md"
    out.write_text("\n".join(md), encoding="utf-8", newline="\n")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
