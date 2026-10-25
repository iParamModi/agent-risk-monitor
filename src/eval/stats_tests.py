"""Paired tests between two settings on the same records (decisions.md R10.4).

- Wilcoxon signed-rank on checks per case: is the check saving real?
- McNemar (exact binomial) on per-case correctness: is the accuracy difference real?
Both are run per record (as R10.4 says) and per seed as a cross-check, because records of one
seed are near-copies. Per seed: the seed's mean checks / mean correctness, compared with Wilcoxon.
Two-sided everywhere.
"""
from collections import defaultdict

from scipy.stats import binomtest, wilcoxon

from src.eval.metrics import decision_cases, is_correct


def paired(cases_a: list[dict], cases_b: list[dict]) -> list[tuple[dict, dict]]:
    """(a, b) per record_id; both settings must hold exactly the same records."""
    a = {c["record_id"]: c for c in cases_a}
    b = {c["record_id"]: c for c in cases_b}
    if set(a) != set(b) or len(a) != len(cases_a) or len(b) != len(cases_b):
        raise ValueError("both settings must hold the same records, each once")
    return [(a[r], b[r]) for r in sorted(a)]


def seed_means(pairs: list[tuple[dict, dict]], value) -> tuple[list[float], list[float]]:
    groups = defaultdict(list)
    for a, b in pairs:
        groups[a["seed_id"]].append((value(a), value(b)))
    xs = [sum(v[0] for v in g) / len(g) for g in groups.values()]
    ys = [sum(v[1] for v in g) / len(g) for g in groups.values()]
    return xs, ys


def wilcoxon_test(xs: list[float], ys: list[float]) -> dict:
    diffs = [x - y for x, y in zip(xs, ys)]
    out = {"n": len(diffs), "n_nonzero": sum(d != 0 for d in diffs),
           "mean_a": sum(xs) / len(xs) if xs else None, "mean_b": sum(ys) / len(ys) if ys else None}
    if out["n_nonzero"] == 0:     # no difference anywhere: nothing to test
        return {**out, "statistic": None, "p_value": 1.0}
    r = wilcoxon(xs, ys, zero_method="wilcox", alternative="two-sided")
    return {**out, "statistic": float(r.statistic), "p_value": float(r.pvalue)}


def n_calls(case: dict) -> float:
    return float(len(case["calls"]))


def correct(case: dict) -> float:
    return float(is_correct(case))


def wilcoxon_checks(cases_a: list[dict], cases_b: list[dict], by: str = "case") -> dict:
    """Checks per case, a vs b (e.g. selective vs always). by = "case" or "seed"."""
    pairs = paired(cases_a, cases_b)
    if by == "seed":
        xs, ys = seed_means(pairs, n_calls)
    else:
        xs, ys = [n_calls(a) for a, _ in pairs], [n_calls(b) for _, b in pairs]
    return {"test": "wilcoxon", "on": "checks per case", "by": by, **wilcoxon_test(xs, ys)}


def mcnemar_correct(cases_a: list[dict], cases_b: list[dict]) -> dict:
    """Per record: only the records where exactly one setting is right count (exact binomial test)."""
    pairs = [(a, b) for a, b in paired(cases_a, cases_b) if a.get("task", "decide_action") == "decide_action"]
    only_a = sum(is_correct(a) and not is_correct(b) for a, b in pairs)
    only_b = sum(is_correct(b) and not is_correct(a) for a, b in pairs)
    p = binomtest(only_a, only_a + only_b, 0.5).pvalue if only_a + only_b else 1.0
    return {"test": "mcnemar_exact", "on": "decision correct", "by": "case", "n": len(pairs),
            "only_a_right": only_a, "only_b_right": only_b, "p_value": float(p)}


def accuracy_by_seed(cases_a: list[dict], cases_b: list[dict]) -> dict:
    """Seed-level cross-check of McNemar: per-seed accuracy, a vs b, Wilcoxon."""
    pairs = paired(decision_cases(cases_a), decision_cases(cases_b))
    xs, ys = seed_means(pairs, correct)
    return {"test": "wilcoxon", "on": "decision correct", "by": "seed", **wilcoxon_test(xs, ys)}


def compare(cases_a: list[dict], cases_b: list[dict]) -> dict:
    """All R10.4 tests for one pair of settings, per case and per seed."""
    return {
        "checks": {"by_case": wilcoxon_checks(cases_a, cases_b), "by_seed": wilcoxon_checks(cases_a, cases_b, "seed")},
        "correct": {"by_case": mcnemar_correct(cases_a, cases_b), "by_seed": accuracy_by_seed(cases_a, cases_b)},
    }
