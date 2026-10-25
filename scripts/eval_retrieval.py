"""Retrieval quality on the IN-DOMAIN seeds, for w = 0.0, 0.1, ..., 1.0 (PLAN Step 6.4).

  python scripts/eval_retrieval.py

First estimate only: our records do not exist yet, so the query is the seed's proposed action +
story_hint (stand-in for the last user request), and the policies are the temporary store.
OOD seeds are never used here (no tuning on OOD or test). Final w: tuned on the val seeds once
Step 5 (policies) and Step 11 (seed split) are done.

Writes outputs/retrieval/seed_report_in_domain.json and .md.
"""
import glob
import sys
from collections import defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.common.io import REPO_ROOT, write_json  # noqa: E402
from src.policies.retriever import Retriever, build_query, combine, top_indices  # noqa: E402
from src.policies.store import load_policies  # noqa: E402

SEED_DIR = REPO_ROOT / "data" / "seeds" / "in_domain"
OUT_DIR = REPO_ROOT / "outputs" / "retrieval"
W_VALUES = [round(0.1 * i, 1) for i in range(11)]
DEPTH = 5


def load_seeds(folder=SEED_DIR) -> list[dict]:
    return [yaml.safe_load(Path(f).read_text(encoding="utf-8")) for f in sorted(glob.glob(str(folder / "*.yaml")))]


def rate(num: int, den: int) -> float | None:
    return num / den if den else None


def score_ranking(golds: list[list[str]], ranked: list[list[str]], case_types: list[str]) -> dict:
    """recall@k = gold policy (any, if several) in the top k; full recall@3 = all gold policies in
    the top 3; conflict recall = full recall@3 on T5 seeds with two gold policies."""
    hit = lambda g, r, k: bool(set(g) & set(r[:k]))   # noqa: E731
    full = [set(g) <= set(r[:3]) for g, r in zip(golds, ranked)]
    conflict = [f for f, g, ct in zip(full, golds, case_types) if ct == "T5" and len(g) >= 2]
    n = len(golds)
    return {
        "seeds": n,
        "recall@1": rate(sum(hit(g, r, 1) for g, r in zip(golds, ranked)), n),
        "recall@3": rate(sum(hit(g, r, 3) for g, r in zip(golds, ranked)), n),
        "recall@5": rate(sum(hit(g, r, 5) for g, r in zip(golds, ranked)), n),
        "full_recall@3": rate(sum(full), n),
        "conflict_recall@3": rate(sum(conflict), len(conflict)),
        "conflict_seeds": len(conflict),
    }


def choose_w(by_w: dict[float, dict]) -> float:
    """Highest recall@3; on a tie, the w closest to 0.5."""
    return max(by_w, key=lambda w: (by_w[w]["recall@3"], -abs(w - 0.5)))


def evaluate(seeds: list[dict], retriever: Retriever) -> dict:
    ids = [p["policy_id"] for p in retriever.policies]
    golds = [s["gold_policy_ids"] for s in seeds]
    cts = [s["case_type"] for s in seeds]
    raw = [retriever.raw_scores(build_query(s["proposed_action"], s.get("story_hint"))) for s in seeds]
    ranked_by_w = {w: [[ids[i] for i in top_indices(combine(k, m, w), DEPTH)] for k, m in raw] for w in W_VALUES}
    by_w = {w: score_ranking(golds, ranked_by_w[w], cts) for w in W_VALUES}
    best = choose_w(by_w)
    ranked = ranked_by_w[best]
    groups = defaultdict(list)
    for s, g, r in zip(seeds, golds, ranked):
        groups[("domain", s["domain"])].append((g, r, s["case_type"]))
        groups[("case_type", s["case_type"])].append((g, r, s["case_type"]))
    breakdown = defaultdict(dict)
    for (kind, value), rows in sorted(groups.items()):
        breakdown[kind][value] = score_ranking(*map(list, zip(*rows)))
    misses = [{"seed_id": s["seed_id"], "gold": g, "top3": r[:3]}
              for s, g, r in zip(seeds, golds, ranked) if not set(g) & set(r[:3])]
    return {"by_w": {str(w): v for w, v in by_w.items()}, "chosen_w": best,
            "at_chosen_w": {"overall": by_w[best], **breakdown, "misses": misses}}


def pct(x) -> str:
    return "–" if x is None else f"{100 * x:.1f}"


def to_markdown(report: dict) -> str:
    lines = ["# Retrieval on in-domain seeds (first estimate)", "",
             f"Policies: {report['policies']} (temporary store). Seeds: {report['seeds']}. "
             "Query = proposed action + story_hint. score = w · embeddings + (1 − w) · BM25.",
             "", "| w | recall@1 | recall@3 | recall@5 | all gold in top 3 | T5 conflict recall@3 |",
             "|---|---|---|---|---|---|"]
    for w, r in report["by_w"].items():
        mark = " ←" if float(w) == report["chosen_w"] else ""
        lines.append(f"| {w}{mark} | {pct(r['recall@1'])} | {pct(r['recall@3'])} | {pct(r['recall@5'])} | "
                     f"{pct(r['full_recall@3'])} | {pct(r['conflict_recall@3'])} |")
    at = report["at_chosen_w"]
    lines += ["", f"Best w = {report['chosen_w']} (highest recall@3; ties go to the w closest to 0.5). "
              "Not final: w is tuned on val seeds after Step 5 + the seed split.", ""]
    for kind in ("domain", "case_type"):
        lines += [f"## recall@3 by {kind} (w = {report['chosen_w']})", "", f"| {kind} | seeds | recall@3 |", "|---|---|---|"]
        lines += [f"| {k} | {v['seeds']} | {pct(v['recall@3'])} |" for k, v in at[kind].items()]
        lines.append("")
    lines += [f"## Misses at w = {report['chosen_w']} ({len(at['misses'])})", "", "| seed | gold | top 3 |", "|---|---|---|"]
    lines += [f"| {m['seed_id']} | {', '.join(m['gold'])} | {', '.join(m['top3'])} |" for m in at["misses"]]
    return "\n".join(lines) + "\n"


def main() -> int:
    policies = load_policies()
    seeds = load_seeds()
    report = {"policies": len(policies), "seeds": len(seeds), "query": "proposed_action + story_hint",
              "w_values": W_VALUES, **evaluate(seeds, Retriever(policies))}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(OUT_DIR / "seed_report_in_domain.json", report)
    (OUT_DIR / "seed_report_in_domain.md").write_text(to_markdown(report), encoding="utf-8")
    for w, r in report["by_w"].items():
        print(f"w={w}: recall@3 {pct(r['recall@3'])}  conflict {pct(r['conflict_recall@3'])}")
    print(f"best w = {report['chosen_w']}; report in {OUT_DIR.relative_to(REPO_ROOT)}/seed_report_in_domain.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
