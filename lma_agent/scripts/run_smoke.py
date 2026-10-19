"""Run the smoke tasks against the agent model on Groq and print one row per task.

Usage: python -m lma_agent.scripts.run_smoke [--gate allow|block|ask|escalate] [--task <task_id>]
"""
import argparse

from lma_agent.agent.gate import allow_all, fake_gate
from lma_agent.agent.llm import make_client
from lma_agent.agent.loop import run_agent
from lma_agent.config import MODEL, RUNS_DIR
from lma_agent.sim.models import EpisodeResult, Task
from lma_agent.sim.seed_state import apply_overrides, build_seed_state
from lma_agent.tasks.load_tasks import SMOKE_TASKS, load_tasks

GATES = {
    "allow": allow_all,
    "block": fake_gate("BLOCK"),
    "ask": fake_gate("ASK_CONFIRMATION"),
    "escalate": fake_gate("ESCALATE"),
}
COLUMNS = ["task_id", "status", "steps", "tools_used", "errors", "writes_done", "expected_ok", "missing"]


def tools_used(result: EpisodeResult) -> list[str]:
    """Tool names the agent called, in first-use order."""
    return list(dict.fromkeys(s.proposed_action.name for s in result.steps))


def compare_tools(expected: list[str], used: list[str]) -> dict:
    """Tool-choice check: which expected tools were missed and which extra tools were used."""
    return {"ok": set(expected) <= set(used),
            "missing": sorted(set(expected) - set(used)),
            "extra": sorted(set(used) - set(expected))}


def summarize(task: Task, result: EpisodeResult) -> dict:
    """One table row for a finished episode."""
    used = tools_used(result)
    check = compare_tools(task.expected_tools, used)
    return {"task_id": task.task_id, "status": result.status, "steps": result.n_llm_calls,
            "tools_used": ",".join(used), "errors": result.n_tool_errors,
            "writes_done": sum(s.tool_type == "write" and s.executed for s in result.steps),
            "expected_ok": check["ok"], "missing": ",".join(check["missing"]),
            "episode_id": result.episode_id}


def run_task(task: Task, client, gate) -> EpisodeResult:
    """Run one task on a fresh state and save the episode to runs/."""
    state = apply_overrides(build_seed_state(task.state_seed), task.overrides)
    return run_agent(task, state, client, gate=gate, out_dir=RUNS_DIR)


def format_table(rows: list[dict]) -> str:
    """Plain-text table of the rows plus the expected-tool hit rate."""
    widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in COLUMNS}
    lines = ["  ".join(c.ljust(widths[c]) for c in COLUMNS)]
    lines += ["  ".join(str(r[c]).ljust(widths[c]) for c in COLUMNS) for r in rows]
    hits = sum(r["expected_ok"] for r in rows)
    lines.append(f"\nexpected tools used: {hits}/{len(rows)} tasks")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> list[dict]:
    """Parse CLI args, run the tasks, print the table and return the rows."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", choices=sorted(GATES), default="allow")
    parser.add_argument("--task", help="run only this task_id")
    parser.add_argument("--tasks", default=str(SMOKE_TASKS), help="tasks YAML file")
    args = parser.parse_args(argv)

    tasks = [t for t in load_tasks(args.tasks) if not args.task or t.task_id == args.task]
    if not tasks:
        parser.error(f"no task named {args.task}")
    client = make_client()
    print(f"model={MODEL} gate={args.gate} tasks={len(tasks)}")
    rows = []
    for task in tasks:
        row = summarize(task, run_task(task, client, GATES[args.gate]))
        rows.append(row)
        print(f"  {row['task_id']}: {row['status']} ({row['episode_id']}.json)")
    print(format_table(rows))
    return rows


if __name__ == "__main__":
    main()
