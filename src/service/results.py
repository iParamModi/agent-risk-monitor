"""The report's final numbers for the website (GET /api/results), read from the generated results file of the final
system (v2): docs/reports/final_results_v2.json, made by scripts/final_results.py --version v2, the same file the
report's tables (final_results_v2.md, final_report_results.md section 3b) are rendered from. Nothing is typed by
hand or recomputed: values are passed through as fractions (the page shows them in %), with their 95% intervals.
tests/test_results_api.py checks every value against the rendered final_results_v2.md.
"""
import json

from src.common.io import REPO_ROOT

RESULTS_JSON = REPO_ROOT / "docs" / "reports" / "final_results_v2.json"
RESULTS_MD = REPO_ROOT / "docs" / "reports" / "final_results_v2.md"
REPORT_PDF = "report/final_submission.pdf"
SPLITS = {"val": "Val", "test": "Test (locked, in-domain)", "ood": "OOD (locked, out-of-domain)"}
CONDITIONS = {"retrieval": "retrieved policies, tag-filtered top 8 (the full system)",
              "gold": "gold policies + 2 look-alikes (retrieval assumed perfect)"}
METHODS = {"rules": "Rules", "base": "Base Qwen3-8B", "phase_b": "Phase B (QLoRA)"}
RULE_LABELS = {"never": "Rules only", "always": "Rules + environment"}
SETTINGS = ("never", "always", "selective", "oracle")


def _ci(c: dict) -> dict:
    return {"value": c["value"], "low": c["low"], "high": c["high"]}


def _row(method: str, label: str, setting: str, s: dict, saving) -> dict:
    return {"method": method, "label": label, "setting": setting, "cases": s["cases"],
            "accuracy": _ci(s["ci"]["accuracy"]), "unsafe_action_rate": s["unsafe_action_rate"],
            "wrong_block_rate": s["wrong_block_rate"], "decision_macro_f1": s["decision_f1"]["macro"],
            "checks_per_case": s["checks_per_case"], "saving_vs_always": saving,
            "check_precision": s["check_precision"], "check_recall": s["check_recall"],
            "correct_missing_fact": s["correct_missing_fact"],
            "invalid": round(s["cases"] * (1 - (s.get("valid_json_rate") or 0)))}


def load_results(path=RESULTS_JSON) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    tables = []
    for split, split_name in SPLITS.items():
        for cond, cond_name in CONDITIONS.items():
            reports = data.get(f"{split}_{cond}")
            if not reports:
                continue
            rows, versus = [], []
            if "rules" in reports:
                r = reports["rules"]
                for s, label in RULE_LABELS.items():
                    rows.append(_row("rules", label, s, r["settings"][s], r.get("saving", {}).get(s)))
            for model in ("base", "phase_b"):
                r = reports.get(model)
                if not r:
                    continue
                for s in SETTINGS:
                    rows.append(_row(model, METHODS[model], s, r["settings"][s], r["saving"].get(s)))
                h, t = r["hypothesis"], r["selective_vs_always"]
                checks = t["tests"]["checks"]["by_case"]
                versus.append({"method": model, "label": METHODS[model],
                               "unsafe_diff": _ci(h), "margin": h["margin"], "hypothesis_passes": h["passes"],
                               "accuracy_diff": _ci(t["accuracy_diff"]),
                               "mcnemar_p": t["tests"]["correct"]["by_case"]["p_value"],
                               "checks_selective": checks["mean_a"], "checks_always": checks["mean_b"],
                               "checks_p": checks["p_value"], "oracle_saving": r.get("oracle_saving")})
            tables.append({"split": split, "split_name": split_name, "policies": cond, "policies_name": cond_name,
                           "cases": rows[0]["cases"] if rows else None, "rows": rows, "selective_vs_always": versus})
    return {"system": "v2 (final)", "source": str(path.relative_to(REPO_ROOT)),
            "rendered_tables": str(RESULTS_MD.relative_to(REPO_ROOT)), "report": REPORT_PDF,
            "hypothesis_rule": "R10.4: selective is not less safe than always if the upper bound of the difference in "
                               "unsafe-action rate (selective minus always) is at most 5 points",
            "tables": tables}
