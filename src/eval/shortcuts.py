"""Shortcut check of the collected datasets (R-Judge, ATBench, AgentRisk): how much of the models' risk-label score a
surface feature could explain. No GPU; scores come from the run folders of the Kaggle jobs. Counts and scores only
(AgentRisk has no licence); --words prints a word model's top words to the terminal, never to the report.

    python -m src.eval.shortcuts [--words]     # -> docs/reports/shortcut_check_tables.md

Three checks, each on val and test:
1. Word models: TF-IDF + logistic regression, one per dataset, trained on its train split with fixed settings (no
   tuning), on the whole record or on the judged step only. A model that barely beats these may only read wording.
2. Named cues: how the cue splits SAFE and UNSAFE on train, what a rule using only the cue scores, and how the models
   do on the records where it points the wrong way.
3. Near-copies: test records with a very similar record in the Phase A training list (cosine of TF-IDF vectors).

Only visible text is read, plus gold to score. Records over the eval token limit are left out, as in the model runs.
"""
import argparse
import json
import re
from pathlib import Path

from src.common.io import REPO_ROOT, read_jsonl
from src.eval.tables import pct, table

KAGGLE = REPO_ROOT / "outputs" / "kaggle"
EXTERNAL = REPO_ROOT / "data" / "external"
SOURCES = {"r_judge": "R-Judge", "atbench": "ATBench", "agentrisk": "AgentRisk"}
MODELS = {"base": "Base", "phase_a": "Phase A", "phase_b": "Phase B"}
VAL_RUNS = {"base": "base_eval/results/runs/base_qwen3_8b_fp16_{}",
            "phase_a": "lora_eval/results/runs/lora_phase_a_qwen3_8b_{}",
            "phase_b": "finetune_phase_b/results/runs/lora_phase_b_qwen3_8b_{}"}
MAX_TOKENS = 7300               # kaggle/base_eval/run_base_eval.py
NEAR_COPY = 0.7
CUE_ODDS = 3                    # a cue is reported if one label has it at least this many times as often on train
MIN_CUE_RECORDS = 10
INJECTION = re.compile(r"ignore (all |any )?(previous|prior|above)|disregard (all|the|any|previous)|new instructions?"
                       r"|system override|you must now", re.I)


def is_unsafe(record: dict) -> bool:
    return record["gold"]["risk_label"] == "UNSAFE"


def full_text(record: dict) -> str:
    """Everything the record shows the monitor, each part once."""
    v = record["visible"]
    parts = [t.get("text") or "" for t in v["trajectory"]] + [t.get("action_text") or "" for t in v["trajectory"]]
    parts += [json.dumps(t["tool_call"]) for t in v["trajectory"] if t.get("tool_call")]
    return " ".join(parts) + " " + proposed_text(record)


def proposed_text(record: dict) -> str:
    v = record["visible"]
    action = json.dumps(v["proposed_action"]) if v.get("proposed_action") else ""
    return (action + " " + (v.get("proposed_action_text") or "")).strip()


def step_text(record: dict) -> str:
    """The step to judge: the proposed action, or the last agent turn when the record has none."""
    step = proposed_text(record)
    if step:
        return step
    agent = [t for t in record["visible"]["trajectory"] if t["role"] == "agent"]
    return " ".join(filter(None, (agent[-1].get("text"), agent[-1].get("action_text")))) if agent else ""


def tool_text(record: dict) -> str:
    return " ".join(t.get("text") or "" for t in record["visible"]["trajectory"] if t["role"] == "tool")


CUES = {
    "tool status error": lambda r: bool(re.search(r"status\W{1,4}error", tool_text(r), re.I)),
    "word `error` in a tool output": lambda r: "error" in tool_text(r).lower(),
    "injection-like text": lambda r: bool(INJECTION.search(full_text(r))),
    "HTML page in a tool output": lambda r: bool(re.search(r"<!doctype|<html", tool_text(r), re.I)),
    "step is a reply to the user": lambda r: "reply_to_user" in (r["meta"].get("flags") or []),
    "over 2,000 tokens": lambda r: r["meta"]["n_tokens"] > 2000,
}


def cue_rule(cue, train: list[dict]):
    """A rule that uses only the cue: the cue's side is whichever label has it more often on train. None if the cue
    does not separate the labels on train (too rare, or under CUE_ODDS to 1)."""
    has = [r for r in train if cue(r)]
    unsafe = sum(map(is_unsafe, has))
    if len(has) < MIN_CUE_RECORDS or max(unsafe, len(has) - unsafe) < CUE_ODDS * min(unsafe, len(has) - unsafe):
        return None
    return lambda r: cue(r) == (2 * unsafe >= len(has))


def load_records(source: str) -> list[dict]:
    return list(read_jsonl(EXTERNAL / f"{source}.jsonl"))


def in_eval(record: dict, split: str) -> bool:
    return record["split"] == split and record["meta"]["n_tokens"] <= MAX_TOKENS


def predictions(split: str) -> dict[str, dict[str, str | None]]:
    """model -> record_id -> predicted risk label (None when the output was invalid)."""
    out = {}
    for model in MODELS:
        out[model] = {}
        for source in SOURCES:
            folder = (KAGGLE / "collected_test/results/runs" / f"collected_{model}_{source}_test" if split == "test"
                      else KAGGLE / VAL_RUNS[model].format(source))
            for c in read_jsonl(folder / "predictions.jsonl"):
                out[model][c["record_id"]] = (c["output"] or {}).get("risk_label")
    return out


def word_model(train: list[dict], text, words: str | None = None):
    """Trained on train only; returns predict(records) -> [is unsafe]."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    clf = LogisticRegression(C=10, max_iter=3000).fit(vec.fit_transform(map(text, train)), list(map(is_unsafe, train)))
    if words:
        names, order = vec.get_feature_names_out(), clf.coef_[0].argsort()
        print(f"{words}\n  UNSAFE: {list(names[order[-15:]])}\n  SAFE:   {list(names[order[:15]])}")
    return lambda records: [bool(p) for p in clf.predict(vec.transform(map(text, records)))]


def right(pred: dict, records: list[dict]) -> str:
    """'<right> of <n>' for one model."""
    return f"{sum(pred[r['record_id']] == r['gold']['risk_label'] for r in records)} of {len(records)}"


def share(flags: list[bool]) -> str:
    return pct(sum(flags) / len(flags)) if flags else "–"


def mcnemar(a: list[bool], b: list[bool]) -> tuple[int, int, float]:
    """(only a right, only b right, exact two-sided p) over the same records."""
    from scipy.stats import binomtest
    only_a, only_b = sum(x and not y for x, y in zip(a, b)), sum(y and not x for x, y in zip(a, b))
    return only_a, only_b, binomtest(only_a, only_a + only_b, 0.5).pvalue if only_a + only_b else 1.0


def report_split(split: str, data: dict, show_words: bool) -> list[str]:
    preds = predictions(split)
    score, cues, hard, tests = [], [], [], []
    pooled = {"gold": [], "whole record": [], "judged step": [], **{m: [] for m in MODELS}}
    for source, name in SOURCES.items():
        records, train = data[source], [r for r in data[source] if r["split"] == "train"]
        ev = [r for r in records if in_eval(r, split)]
        gold = list(map(is_unsafe, ev))
        said = {}
        for key, text in (("whole record", full_text), ("judged step", step_text)):
            said[key] = word_model(train, text, f"{name}, {key}" if show_words and split == "test" else None)(ev)
        score.append([name, str(len(ev)), *(share([preds[m][r["record_id"]] == r["gold"]["risk_label"] for r in ev])
                                            for m in MODELS),
                      share([s == g for s, g in zip(said["whole record"], gold)]),
                      share([s == g for s, g in zip(said["judged step"], gold)]), share(gold)])
        pooled["gold"] += gold
        for key in ("whole record", "judged step"):
            pooled[key] += [x == g for x, g in zip(said[key], gold)]
        for m in MODELS:
            pooled[m] += [preds[m][r["record_id"]] == r["gold"]["risk_label"] for r in ev]
        for m in ("phase_a", "phase_b"):
            only_m, only_word, p_value = mcnemar([preds[m][r["record_id"]] == r["gold"]["risk_label"] for r in ev],
                                                 [x == g for x, g in zip(said["judged step"], gold)])
            tests.append([name, MODELS[m], str(only_m), str(only_word), f"{p_value:.3f}"])
        step_wrong = [r for r, s, g in zip(ev, said["judged step"], gold) if s != g]
        hard.append([name, "the step's word model is wrong", *(right(preds[m], step_wrong) for m in MODELS)])
        for cue_name, cue in CUES.items():
            rule = cue_rule(cue, train)
            if rule is None:
                continue
            train_has = [r for r in train if cue(r)]
            ev_has = [r for r in ev if cue(r)]
            against = [r for r in ev if rule(r) != is_unsafe(r)]
            cues.append([name, cue_name, f"{sum(not is_unsafe(r) for r in train_has)} / {sum(map(is_unsafe, train_has))}",
                         f"{sum(not is_unsafe(r) for r in ev_has)} / {sum(map(is_unsafe, ev_has))}",
                         share([rule(r) == is_unsafe(r) for r in ev]), *(right(preds[m], against) for m in MODELS)])
    score.append(["**All**", str(len(pooled["gold"])), *(share(pooled[m]) for m in MODELS),
                  share(pooled["whole record"]), share(pooled["judged step"]), share(pooled["gold"])])
    for m in ("phase_a", "phase_b"):
        only_m, only_word, p_value = mcnemar(pooled[m], pooled["judged step"])
        tests.append(["**All**", MODELS[m], str(only_m), str(only_word), f"{p_value:.3f}"])
    no_reply = [r for r in data["agentrisk"] if in_eval(r, split) and not CUES["step is a reply to the user"](r)]
    for label, unsafe in (("SAFE", False), ("UNSAFE", True)):
        part = [r for r in no_reply if is_unsafe(r) == unsafe]
        hard.append(["AgentRisk", f"step is not a reply to the user, {label}", *(right(preds[m], part) for m in MODELS)])
    plain = [r for r in data["atbench"] if in_eval(r, split) and is_unsafe(r) and not CUES["tool status error"](r)]
    hard.append(["ATBench", "UNSAFE with no tool status error", *(right(preds[m], plain) for m in MODELS)])
    return [f"## {split.capitalize()}", "", "### Safe/unsafe accuracy: models next to word models", "",
            *table(["Dataset", "Records", *MODELS.values(), "Word model, whole record", "Word model, judged step",
                    "Share UNSAFE"], score), "",
            "### Model vs the judged step's word model (exact McNemar)", "",
            *table(["Dataset", "Model", "Only the model right", "Only the word model right", "p"], tests), "",
            f"### Named cues (SAFE / UNSAFE counts; cues under {CUE_ODDS} to 1 on train are left out)", "",
            *table(["Dataset", "Cue", "On train", f"On {split}", "Rule using only the cue, accuracy",
                    *(f"{m}, right where the cue misleads" for m in MODELS.values())], cues), "",
            "### Harder subsets (right of records)", "", *table(["Dataset", "Records where", *MODELS.values()], hard), ""]


def near_copies(data: dict, split: str) -> list[list[str]]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    pool = {x.strip() for x in (EXTERNAL / "splits" / "phase_a_train.txt").read_text(encoding="utf-8").split()}
    preds, rows = predictions(split), []
    for source, name in SOURCES.items():
        trained = [r for r in data[source] if r["record_id"] in pool]
        ev = [r for r in data[source] if in_eval(r, split)]
        vec = TfidfVectorizer(sublinear_tf=True)
        sims = (vec.fit(map(full_text, trained)).transform(map(full_text, ev))
                @ vec.transform(map(full_text, trained)).T).toarray()
        nearest, best = sims.argmax(1), sims.max(1)
        for label, keep in (("near-copy", lambda s: s >= NEAR_COPY), ("the rest", lambda s: s < NEAR_COPY)):
            part = [i for i in range(len(ev)) if keep(best[i])]
            if not part:
                continue
            rows.append([name, label, str(len(part)),
                         f"{sum(is_unsafe(trained[nearest[i]]) == is_unsafe(ev[i]) for i in part)} of {len(part)}",
                         *(right(preds[m], [ev[i] for i in part]) for m in MODELS)])
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--words", action="store_true", help="print each word model's top words (terminal only)")
    ap.add_argument("--out", default=str(REPO_ROOT / "docs" / "reports" / "shortcut_check_tables.md"))
    args = ap.parse_args(argv)
    data = {s: load_records(s) for s in SOURCES}
    md = ["# Shortcut check of the collected datasets: tables", "",
          "Generated by `python -m src.eval.shortcuts`; findings are in `shortcut_check.md`. Counts and scores only.", ""]
    for split in ("test", "val"):
        md += report_split(split, data, args.words)
        md += [f"### Near-copies of a Phase A training record (similarity at least {NEAR_COPY})", "",
               *table(["Dataset", "Records", "Count", "Nearest training record has the same label",
                       *MODELS.values()], near_copies(data, split)), ""]
    Path(args.out).write_text("\n".join(md), encoding="utf-8", newline="\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
