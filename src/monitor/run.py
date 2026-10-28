"""Run the monitor on records and write outputs/runs/<run_id>/predictions.jsonl (+ run_config.json).

    python -m src.monitor.run --records data/external/r_judge.jsonl --split val --setting selective \
        --model Qwen/Qwen3-8B --base-url http://localhost:8000/v1 --run-id qwen3_8b_val_selective --limit 10

The API key is read from the env var named by --api-key-env (default MONITOR_API_KEY, .env is loaded).
--dry-run uses a FakeModel that always gives a fixed valid answer, to test the pipeline without a GPU.
--backend transformers loads the model on local GPUs instead (Kaggle; kaggle/README.md):
    python -m src.monitor.run --records ... --setting never --backend transformers \
        --model Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218 [--adapter <LoRA>] --run-id ...

Our records (task = decide_action) get the top 3 retrieved policies, the check-tool list, a gateway per record
and the always-setting checks (src/monitor/case_inputs.py), e.g. all 4 settings on our val records:
    for s in never always selective oracle; do python -m src.monitor.run --records data/records/val.jsonl \
        --setting $s --backend transformers --model Qwen/Qwen3-8B --revision ... --adapter <LoRA> --run-id ours_$s; done
For our records the run also writes traces.jsonl: per record, every pass (prompt and raw answer), every gateway
call with its result, which policies were shown (and whether the gold ones were), and the final output; read it
with python scripts/show_traces.py outputs/runs/<run_id>. --dry-run on our records answers with a scripted model
(selective: ask for the first table check, then ALLOW), so the gateway, retrieval and scoring run without a GPU.
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
        self.passes: list[dict] = []        # prompt + raw answer of every pass of the current record

    def generate(self, messages):
        gen = self.inner.generate(messages)
        self.texts.append(gen.text)
        self.passes.append({"messages": messages, "answer": gen.text})
        return gen


class RecordingGateway:
    """Wraps a gateway and keeps each call with the result the monitor saw (for traces.jsonl)."""

    def __init__(self, gateway):
        self.inner, self.calls = gateway, []

    def call(self, tool, args):
        result = self.inner.call(tool, args)
        self.calls.append({"tool": tool, "args": args, "result": result})
        return result


def scripted_answers(setting: str, table_checks: list[dict]) -> list[str]:
    """--dry-run on our records: selective asks for the first table check, then every setting answers ALLOW."""
    decide = json.dumps({"type": "DECISION", "decision": "ALLOW", "risk_label": "SAFE", "risk_type": "NONE",
                         "evidence": {"facts": [], "policy_ids": ["1"]}})
    if setting == "selective" and table_checks:
        need = json.dumps({"type": "NEED_INFORMATION", "reason": "Dry run.", "missing_fact": "dry run",
                           "checks": [table_checks[0]]})
        return [need, decide]
    return [decide]


def trace(record: dict, setting: str, kwargs: dict, passes: list[dict], calls: list[dict], row: dict) -> dict:
    """One record's run for a human to read (scripts/show_traces.py). Gold is copied for the reader only."""
    from src.monitor.prompt_builder import number_policies
    shown = number_policies(kwargs["policies"], record["record_id"])
    gold = record["gold"]
    output = row["output"]
    return {"record_id": record["record_id"], "setting": setting, "case_type": record["case_type"],
            "subtype": record["subtype"], "pair_side": record["pair_side"],
            "gold": {k: gold[k] for k in ("decision", "risk_label", "risk_type", "check_needed", "missing_fact",
                                          "required_checks", "policy_ids")},
            "shown_policies": [{"ref": p["ref"], "policy_id": p["policy_id"], "text": p["text"]} for p in shown],
            "gold_policies_shown": all(pid in {p["policy_id"] for p in shown} for pid in gold["policy_ids"]),
            "passes": passes, "calls": calls, "output": output,
            "correct": bool(output and output.get("decision") == gold["decision"])}


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
    inputs = None
    if any(r["task"] == "decide_action" for r in records):
        from src.monitor.case_inputs import CaseInputs
        inputs = CaseInputs()

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
    rows, invalid_raw, traces = [], [], []
    start = time.perf_counter()
    for i, rec in enumerate(records, 1):
        model.texts, model.passes = [], []
        kwargs = {}
        if rec["task"] == "decide_action":
            kwargs = inputs.for_record(rec, args.setting, args.run_id)
            kwargs["gateway"] = RecordingGateway(kwargs["gateway"])
            if args.dry_run:
                model.inner = FakeModel(scripted_answers(args.setting, kwargs["table_checks"]))
        elif args.dry_run:
            model.inner = FakeModel([DRY_RISK])
        rows.append(run_monitor(rec, args.setting, model, **kwargs))
        if kwargs:
            traces.append(trace(rec, args.setting, kwargs, model.passes, kwargs["gateway"].calls, rows[-1]))
        if rows[-1]["output"] is None:
            invalid_raw.append({"record_id": rec["record_id"], "raw": [t[:RAW_CHARS] for t in model.texts]})
        if i <= 3 or i % 10 == 0 or i == len(records):     # first records early: shows the speed at once
            print(progress_line(i, len(records), time.perf_counter() - start, rows), flush=True)
    n = write_jsonl(out_dir / "predictions.jsonl", rows)
    write_jsonl(out_dir / "invalid_outputs.jsonl", invalid_raw)
    if traces:              # our records only: external prompts (AgentRisk has no licence) are never written
        write_jsonl(out_dir / "traces.jsonl", traces)
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
