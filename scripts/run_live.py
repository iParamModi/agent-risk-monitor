"""Run one demo task live: the agent works on a fresh company state and every write goes through the real monitor.

    python scripts/run_live.py --task demo_hidden --model fake                       # CPU, no API, no GPU
    python scripts/run_live.py --task demo_acmepay --model transformers --adapter /kaggle/input/... --confirm no

--model     fake = RuleFakeMonitor (rules, NOT the trained model); transformers = Qwen3-8B (+ --adapter) on local
            GPUs (Kaggle); openai = an OpenAI-compatible endpoint (--base-url; only localhost here, anything else
            goes through the cost guard and is Tier C)
--agent     fake = the scripted agent (src/live/scripted_agent.py); groq = openai/gpt-oss-120b on the Groq free
            tier, through the cost guard (docs/DEPLOYMENT_RULES.md). Default: fake.
--embedder  keyword = BM25 only (CPU, no sentence-transformers); bge = bge-base-en-v1.5 + BM25 (the evaluation
            retriever). Default: keyword with --model fake, bge otherwise.
Writes <out>/<run_id>.jsonl (one event per line, src/live/events.py) and prints one summary line (JSON).
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lma_agent.agent.gate import monitor_gate  # noqa: E402
from lma_agent.agent.loop import run_agent  # noqa: E402
from lma_agent.agent.user_sim import ScriptedUser  # noqa: E402
from lma_agent.sim.seed_state import apply_overrides, build_seed_state  # noqa: E402
from lma_agent.tasks.load_tasks import load_tasks  # noqa: E402
from src.live.events import OUT_DIR, JsonlSink, new_run_id  # noqa: E402
from src.monitor.settings import SETTINGS  # noqa: E402

DEMO_TASKS = ROOT / "lma_agent" / "tasks" / "demo_tasks.yaml"
QWEN = "Qwen/Qwen3-8B"
QWEN_REVISION = "b968826d9c46dd6066d109eabc6255188de91218"


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", required=True)
    ap.add_argument("--tasks-file", default=str(DEMO_TASKS))
    ap.add_argument("--model", choices=("fake", "transformers", "openai"), default="fake")
    ap.add_argument("--model-name", default=QWEN)
    ap.add_argument("--revision", default=QWEN_REVISION)
    ap.add_argument("--adapter", default=None, help="LoRA adapter folder (the final adapter, trained 11 Nov)")
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--api-key-env", default="MONITOR_API_KEY")
    ap.add_argument("--agent", choices=("fake", "groq"), default="fake")
    ap.add_argument("--embedder", choices=("keyword", "bge"), default=None)
    ap.add_argument("--setting", choices=SETTINGS, default="selective")
    ap.add_argument("--k", type=int, default=3, help="retrieved policies shown to the monitor")
    ap.add_argument("--version", choices=("v1", "v2"), default="v2")
    ap.add_argument("--confirm", choices=("yes", "no"), default=None,
                    help="the user's answer to ASK_CONFIRMATION (default: the task's user_confirms)")
    ap.add_argument("--out", default=str(OUT_DIR))
    return ap.parse_args(argv)


def build_model(args):
    if args.model == "fake":
        from src.live.fake_monitor import RuleFakeMonitor
        return RuleFakeMonitor()
    if args.model == "transformers":
        from src.monitor.models import TransformersModel
        return TransformersModel(args.model_name, revision=args.revision, adapter=args.adapter)
    if not args.base_url:
        sys.exit("--model openai needs --base-url")
    host = urlparse(args.base_url).hostname or ""
    if host not in ("localhost", "127.0.0.1", "::1"):
        from src.service.cost_guard import require_paid_ok
        require_paid_ok(f"monitor endpoint {host}", "C", None, command=" ".join(sys.argv), service=host)
    from src.monitor.models import OpenAICompatModel
    return OpenAICompatModel(args.model_name, args.base_url, os.environ.get(args.api_key_env, ""))


def build_agent(args, task_id: str):
    if args.agent == "fake":
        from src.live.scripted_agent import scripted_agent
        return scripted_agent(task_id), "scripted"
    from src.service.cost_guard import require_paid_ok
    require_paid_ok(f"groq agent task {task_id}", "B", 0.0, command=" ".join(sys.argv), service="groq",
                    unit_price="free tier", price_source="https://console.groq.com/settings/billing/plans")
    from lma_agent.agent.llm import make_client
    from lma_agent.config import MODEL
    return make_client(), MODEL


def build_embedder(args):
    kind = args.embedder or ("keyword" if args.model == "fake" else "bge")
    if kind == "keyword":
        from src.live.monitor_gate import KeywordOnlyEmbedder
        return KeywordOnlyEmbedder(), kind
    from src.policies.retriever import BgeEmbedder
    return BgeEmbedder(), kind


def summarize(task, sink: JsonlSink, run_id: str, path: Path) -> dict:
    decisions = [e.payload for e in sink.events if e.type == "decision"]
    first = decisions[0] if decisions else {}
    exp = task.expected or {}
    row = {"run_id": run_id, "task": task.task_id, "file": str(path),
           "setting": first.get("setting"), "checks_used": first.get("checks_used"),
           "checks_always": first.get("checks_always"), "decision": first.get("decision"),
           "policy_ids": first.get("policy_ids"), "expected_decision": exp.get("decision"),
           "expected_checks": exp.get("checks"), "risk_actions": len(decisions)}
    row["match"] = row["decision"] == row["expected_decision"] if row["expected_decision"] else None
    return row


def run(args) -> dict:
    tasks = {t.task_id: t for t in load_tasks(args.tasks_file)}
    if args.task not in tasks:
        sys.exit(f"unknown task {args.task}; known: {sorted(tasks)}")
    task = tasks[args.task]
    confirms = task.user_confirms if args.confirm is None else args.confirm == "yes"
    suffix = f"confirm_{'yes' if confirms else 'no'}" if args.confirm else ""
    run_id = new_run_id(task.task_id, args.setting, suffix)
    path = Path(args.out) / f"{run_id}.jsonl"

    model = build_model(args)
    client, agent_name = build_agent(args, task.task_id)
    embedder, embedder_name = build_embedder(args)
    gate = monitor_gate(model, setting=args.setting, k=args.k, version=args.version, embedder=embedder,
                        task=task, run_id=run_id)
    meta = {"monitor_model": model.name, "adapter": args.adapter, "agent": agent_name, "setting": args.setting,
            "k": args.k, "version": args.version, "embedder": embedder_name, "confirm": "yes" if confirms else "no",
            "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "expected": task.expected,
            "fake_monitor": args.model == "fake"}
    state = apply_overrides(build_seed_state(task.state_seed), task.overrides)
    sink = JsonlSink(path)
    run_agent(task, state, client, gate=gate, user=ScriptedUser(confirms), on_event=sink, run_id=run_id, meta=meta)
    return summarize(task, sink, run_id, path)


def main(argv=None):
    row = run(parse_args(argv))
    print(json.dumps(row))
    return row


if __name__ == "__main__":
    main()
