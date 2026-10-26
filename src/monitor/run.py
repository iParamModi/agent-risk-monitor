"""Run the monitor on records and write outputs/runs/<run_id>/predictions.jsonl (+ run_config.json).

    python -m src.monitor.run --records data/external/r_judge.jsonl --split val --setting selective \
        --model Qwen/Qwen3-8B --base-url http://localhost:8000/v1 --run-id qwen3_8b_val_selective --limit 10

The API key is read from the env var named by --api-key-env (default MONITOR_API_KEY, .env is loaded).
--dry-run uses a FakeModel that always gives a fixed valid answer, to test the pipeline without a GPU.
--backend transformers loads the model on local GPUs instead (Kaggle; kaggle/README.md):
    python -m src.monitor.run --records ... --setting never --backend transformers \
        --model Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218 [--adapter <LoRA>] --run-id ...

Our records (task = decide_action) also need the check gateway (Step 4), retrieval (Step 6), the
check-tool list (R7.1) and the check table (R7.5); until those exist only external records can run.
"""
import argparse
import json
import os
import time
from datetime import datetime, timezone

from src.common.io import REPO_ROOT, read_jsonl, write_json, write_jsonl
from src.monitor.loop import run_monitor
from src.monitor.models import FakeModel, OpenAICompatModel, TransformersModel
from src.monitor.prompt_builder import template_names
from src.monitor.settings import SETTINGS

RUNS_DIR = REPO_ROOT / "outputs" / "runs"
DRY_RISK = '{"type": "RISK", "risk_label": "SAFE", "risk_type": "NONE"}'


class Recording:
    """Wraps a model and keeps the raw text of each answer, so invalid outputs can be read later
    (predictions.jsonl keeps the eval format, docs/evaluation_metrics.md section 2)."""

    def __init__(self, model):
        self.inner, self.name, self.texts = model, model.name, []

    def generate(self, messages):
        gen = self.inner.generate(messages)
        self.texts.append(gen.text)
        return gen


RAW_CHARS = 1000


def progress_line(done: int, total: int, elapsed_s: float, rows: list[dict]) -> str:
    """'[run] 40/241 (17%) | 6m 10s, ~31m left | invalid 2 | answer 28 tokens on average'"""
    fmt = lambda s: f"{int(s // 60)}m {int(s % 60):02d}s"   # noqa: E731
    left = elapsed_s / done * (total - done) if done else 0
    outs = [r["tokens_out"] for r in rows if r["tokens_out"] is not None]
    avg = f"{sum(outs) / len(outs):.0f}" if outs else "?"
    return (f"[run] {done}/{total} ({100 * done // total}%) | {fmt(elapsed_s)}, ~{fmt(left)} left | "
            f"invalid {sum(r['output'] is None for r in rows)} | answer {avg} tokens on average")


def load_records(paths: list[str], split: str | None, limit: int | None) -> list[dict]:
    records = [r for p in paths for r in read_jsonl(p) if split is None or r["split"] == split]
    return records[:limit] if limit else records


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--records", nargs="+", required=True, help="record .jsonl files")
    ap.add_argument("--split", choices=["train", "val", "test"], default="val")
    ap.add_argument("--setting", choices=SETTINGS, required=True)
    ap.add_argument("--model", help="model name at the endpoint, e.g. Qwen/Qwen3-8B")
    ap.add_argument("--base-url", help="OpenAI-compatible endpoint, e.g. http://localhost:8000/v1 (vLLM)")
    ap.add_argument("--backend", choices=["openai", "transformers"], default="openai")
    ap.add_argument("--revision", help="transformers backend: model revision (commit) to load")
    ap.add_argument("--adapter", help="transformers backend: LoRA adapter folder or Hub id")
    ap.add_argument("--api-key-env", default="MONITOR_API_KEY")
    ap.add_argument("--thinking-off", choices=["template", "none"], default="template")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    records = load_records(args.records, args.split, args.limit)
    ours = [r["record_id"] for r in records if r["task"] == "decide_action"]
    if ours:
        raise SystemExit(f"{len(ours)} decide_action records (e.g. {ours[0]}): the gateway, retriever and "
                         "check-tool list are not built yet (Steps 4, 6, R7.1). Run external records only for now.")

    if args.dry_run:
        model = FakeModel([DRY_RISK] * len(records))
    elif args.backend == "transformers":
        if not args.model:
            raise SystemExit("--model is needed")
        model = TransformersModel(args.model, args.revision, args.adapter)
    else:
        if not (args.model and args.base_url):
            raise SystemExit("--model and --base-url are needed (or --dry-run)")
        from dotenv import load_dotenv
        load_dotenv(REPO_ROOT / ".env")
        model = OpenAICompatModel(args.model, args.base_url, os.getenv(args.api_key_env, ""), args.thinking_off)

    out_dir = RUNS_DIR / args.run_id
    model = Recording(model)
    rows, invalid_raw = [], []
    start = time.perf_counter()
    for i, rec in enumerate(records, 1):
        model.texts = []
        rows.append(run_monitor(rec, args.setting, model))
        if rows[-1]["output"] is None:
            invalid_raw.append({"record_id": rec["record_id"], "raw": [t[:RAW_CHARS] for t in model.texts]})
        if i % 10 == 0 or i == len(records):
            print(progress_line(i, len(records), time.perf_counter() - start, rows), flush=True)
    n = write_jsonl(out_dir / "predictions.jsonl", rows)
    write_jsonl(out_dir / "invalid_outputs.jsonl", invalid_raw)
    write_json(out_dir / "run_config.json", {
        "run_id": args.run_id, "setting": args.setting, "model": model.name, "base_url": args.base_url,
        "thinking_off": args.thinking_off, "backend": args.backend,
        "revision": args.revision, "adapter": args.adapter, "split": args.split, "records": args.records, "n": n,
        "prompts": template_names(), "dry_run": args.dry_run,
        "started": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    invalid = sum(r["output"] is None for r in rows)
    print(json.dumps({"written": str(out_dir / "predictions.jsonl"), "n": n, "invalid": invalid}))


if __name__ == "__main__":
    main()
