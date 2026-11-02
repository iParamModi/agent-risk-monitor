"""Runs the two rule baselines on our records and writes a run folder each, like the monitor runs, so
src.eval.tables can put them next to the model (CPU only, about a minute).

    python -m src.baselines.run --split val test ood [--policies retrieval gold]

Runs: outputs/runs/rules_only_<policies>_<split>, rules_env_<policies>_<split> (predictions.jsonl, run_config.json).
Phase 1 records only (the training filter), as in the model's final run; OOD: all 112. The shown policies are the monitor's
(src.monitor.case_inputs): "retrieval" = the full system's top 3, "gold" = gold + 2 look-alikes. The rules read
the shown policies' text only; gold is copied into each row for scoring, as in every run.
"""
import argparse
import time
from datetime import datetime, timezone

from src.baselines import rules_env, rules_only
from src.common.io import REPO_ROOT, read_jsonl, write_json, write_jsonl
from src.monitor.case_inputs import CaseInputs
from src.monitor.loop import COPIED_FIELDS

BASELINES = {"rules_only": rules_only.run, "rules_env": rules_env.run}
RUNS_DIR = REPO_ROOT / "outputs" / "runs"


def records_for(split: str) -> list[dict]:
    if split == "ood":
        return list(read_jsonl(REPO_ROOT / "data" / "records" / "ood_test.jsonl"))
    from src.training.build_sft import phase1
    return phase1([r for r in read_jsonl(REPO_ROOT / "data" / "records" / f"{split}.jsonl") if r["split"] == split],
                  split)


def row(record: dict, output: dict, calls: list[dict], seconds: float) -> dict:
    out = {k: record[k] for k in COPIED_FIELDS}
    out.update(gold=record["gold"], output=output, calls=calls, passes=0, tokens_in=0, tokens_out=0,
               time_s=round(seconds, 4))
    return out


def run_split(split: str, mode: str, inputs: CaseInputs) -> dict[str, list[dict]]:
    records = records_for(split)
    shown = {r["record_id"]: inputs.policies(r) for r in records}
    out = {}
    for name, baseline in BASELINES.items():
        rows = []
        for r in records:
            start = time.perf_counter()
            output, calls = baseline(r, shown[r["record_id"]])
            rows.append(row(r, output, calls, time.perf_counter() - start))
        run_id = f"{name}_{mode}_{split}"
        write_jsonl(RUNS_DIR / run_id / "predictions.jsonl", rows)
        write_json(RUNS_DIR / run_id / "run_config.json", {
            "run_id": run_id, "baseline": name, "split": split, "policies": mode, "n": len(rows),
            "started": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        right = sum(x["output"]["decision"] == x["gold"]["decision"] for x in rows)
        print(f"{run_id}: decision right {right}/{len(rows)}, gateway calls {sum(len(x['calls']) for x in rows)}")
        out[name] = rows
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", nargs="+", choices=("train", "val", "test", "ood"), default=["val"])
    ap.add_argument("--policies", nargs="+", choices=("retrieval", "gold"), default=["retrieval", "gold"])
    args = ap.parse_args(argv)
    embedder = None
    for mode in args.policies:
        inputs = CaseInputs(embedder=embedder, policy_mode=mode)
        for split in args.split:
            run_split(split, mode, inputs)
        embedder = inputs.embedder
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
