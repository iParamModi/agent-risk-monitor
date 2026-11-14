"""Check the recorded demo runs and write the report's demo table from their summary.json.

    python scripts/demo_table.py                       # outputs/live/demo/ -> docs/reports/demo_table.md
    python scripts/demo_table.py --check-only          # only validate the logs
    python scripts/demo_table.py --runs outputs/live/demo/fake --allow-fake --out /tmp/t.md   # fake-monitor logs

Every number and name in the table and in the three sentences under it is read from summary.json and the run logs
(kaggle/demo_record/demo_record.ipynb wrote them); nothing is typed by hand. A fake-monitor run (the CPU stand-in of
scripts/record_demo_fake.py) is refused unless --allow-fake, and is then named as fake in the text.

Checks on every run of summary.json (validate):
  schema      every line is a src.live.events.Event with the file's run id; company_snapshot, instruction first,
              final_response last
  labels      meta.agent is "scripted" or "groq:<model>"; monitor_version v2 and k = 8 in the meta and in every
              decision; an always run names the selective run it replays, and that run is in the folder
  state       the company state rebuilds from the snapshot and the state_diffs (src.live.company.state_at) and is a
              valid CompanyState; every judged write is followed by a state_diff
  summary     the row's decision, checks, agent, setting and k are the log's
  replay      the replay website lists each run, returns all its events and the company state at every step
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lma_agent.sim.models import CompanyState  # noqa: E402
from lma_agent.tasks.load_tasks import load_tasks  # noqa: E402
from src.live.company import state_at  # noqa: E402
from src.live.events import Event  # noqa: E402
from src.monitor.case_inputs import VERSIONS  # noqa: E402

RUNS = ROOT / "outputs" / "live" / "demo"
OUT = ROOT / "docs" / "reports" / "demo_table.md"
TASKS = ROOT / "lma_agent" / "tasks" / "demo_tasks.yaml"
VERSION = "v2"
DECISIONS = {"ALLOW", "ASK_CONFIRMATION", "BLOCK", "ESCALATE"}
HEAD = ["task", "agent", "setting", "checks used", "checks always", "decision", "expected", "match", "latency"]


def read_log(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def meta_of(events: list[dict]) -> dict:
    return next((e["payload"].get("meta", {}) for e in events if e["type"] == "instruction"), {})


def validate_run(row: dict, folder: Path, run_ids: set[str]) -> list[str]:
    """Problems of one summary row and its log ([] = fine)."""
    name = row.get("run_id") or "?"
    path = folder / str(row.get("file") or "")
    if not row.get("file") or not path.is_file():
        return [f"{name}: log file {row.get('file')!r} is missing"]
    try:
        events = read_log(path)
        for e in events:
            Event.model_validate(e)
    except Exception as err:                                   # bad JSON or an event outside the schema
        return [f"{name}: not a valid event log ({type(err).__name__}: {str(err)[:120]})"]
    out = []
    types = [e["type"] for e in events]
    if types[:2] != ["company_snapshot", "instruction"]:
        out.append(f"{name}: starts with {types[:2]}, not company_snapshot, instruction")
    if not types or types[-1] != "final_response":
        out.append(f"{name}: does not end with final_response")
    if {e["run_id"] for e in events} != {path.stem} or name != path.stem:
        out.append(f"{name}: run id differs between the file name, its events and summary.json")
    meta = meta_of(events)
    agent = str(meta.get("agent") or "")
    if not (agent == "scripted" or (agent.startswith("groq:") and len(agent) > 5)):
        out.append(f"{name}: agent label {agent!r} is not 'scripted' or 'groq:<model>'")
    k = VERSIONS[VERSION]["shown"]
    if meta.get("monitor_version") != VERSION or meta.get("k") != k:
        out.append(f"{name}: meta says monitor {meta.get('monitor_version')} k={meta.get('k')}, not {VERSION} k={k}")
    decisions = [e["payload"] for e in events if e["type"] == "decision"]
    if not decisions:
        out.append(f"{name}: no decision event")
    for d in decisions:
        if d.get("monitor_version") != VERSION or d.get("k") != k:
            out.append(f"{name}: a decision says monitor {d.get('monitor_version')} k={d.get('k')}")
        if d.get("decision") not in DECISIONS:
            out.append(f"{name}: unknown decision {d.get('decision')!r}")
    reused = meta.get("trajectory_reused_from")
    if meta.get("setting") == "always" and not reused:
        out.append(f"{name}: an always run with no trajectory_reused_from")
    if reused and reused not in run_ids:
        out.append(f"{name}: replays the trajectory of {reused}, which is not in this folder")
    try:
        CompanyState.model_validate(state_at(events)["state"])
    except Exception as err:
        out.append(f"{name}: the company state does not rebuild ({type(err).__name__}: {str(err)[:120]})")
    for i, t in enumerate(types):
        if t in ("action_applied", "action_refused") and "state_diff" not in types[i + 1:i + 2]:
            out.append(f"{name}: {t} at event {i + 1} is not followed by a state_diff")
    first = decisions[0] if decisions else {}
    for key, logged in (("decision", first.get("decision")), ("checks_used", first.get("checks_used")),
                        ("checks_always", first.get("checks_always")), ("agent", meta.get("agent")),
                        ("setting", meta.get("setting")), ("k", meta.get("k")),
                        ("monitor_version", meta.get("monitor_version"))):
        if row.get(key) != logged:
            out.append(f"{name}: summary.json {key} = {row.get(key)!r}, the log says {logged!r}")
    return out


def load(folder: Path) -> tuple[list[dict], list[str]]:
    """(summary rows, problems) of a folder of recorded runs."""
    summary = folder / "summary.json"
    if not summary.is_file():
        return [], [f"{summary} is missing"]
    rows = json.loads(summary.read_text(encoding="utf-8"))
    run_ids = {r.get("run_id") for r in rows}
    problems = [p for r in rows for p in validate_run(r, folder, run_ids)]
    listed = {r.get("file") for r in rows}
    problems += [f"{p.name}: a log in the folder that summary.json does not list"
                 for p in sorted(folder.glob("*.jsonl")) if p.name not in listed]
    return rows, problems


def replay_check(rows: list[dict], folder: Path) -> list[str]:
    """Problems when the replay website serves these runs: each run is listed, its events come back whole, and the
    company state is served after every step."""
    from fastapi.testclient import TestClient

    from src.service.app import create_app
    client = TestClient(create_app({"real": folder}))
    listed = {r["run_id"]: r for r in client.get("/api/runs").json()}
    out = []
    for row in rows:
        name = row["run_id"]
        if name not in listed:
            out.append(f"{name}: the website does not list it")
            continue
        if any(listed[name].get(k) != row.get(k) for k in ("decision", "checks_used", "agent", "setting", "k")):
            out.append(f"{name}: the website's summary differs from summary.json")
        res = client.get(f"/api/runs/real/{name}")
        events = res.json()["events"] if res.status_code == 200 else []
        if len(events) != len(read_log(folder / row["file"])):
            out.append(f"{name}: the website does not return every event")
        for step in sorted({e["step"] for e in events}):
            if client.get(f"/api/runs/real/{name}/state", params={"step": step}).status_code != 200:
                out.append(f"{name}: no company state at step {step}")
    return out


def is_fake(row: dict, folder: Path) -> bool:
    return bool(meta_of(read_log(folder / row["file"])).get("fake_monitor"))


def agent_text(agent: str) -> str:
    return "Groq " + agent[5:] if agent.startswith("groq:") else agent


def latency_text(row: dict) -> str:
    passes = [x for x in row.get("latency_s") or [] if x is not None]
    if not passes:
        return ""
    return f"{sum(passes):.1f} s ({len(passes)} pass{'es' if len(passes) != 1 else ''})"


def expected_checks(row: dict):
    """The check count the task expects: its own number for selective, every check of the table for always."""
    return row.get("checks_always") if row.get("setting") == "always" else row.get("expected_checks")


def checks_ok(row: dict) -> bool:
    return expected_checks(row) is None or row.get("checks_used") == expected_checks(row)


def expected_text(row: dict) -> str:
    n = expected_checks(row)
    if n is None:
        return str(row.get("expected_decision") or "")
    return f"{row.get('expected_decision')}, {'all ' if row.get('setting') == 'always' else ''}{count(n, 'check')}"


def match_text(row: dict) -> str:
    if row.get("match") is None:
        return ""
    if not row["match"]:
        return "no"
    return "yes" if checks_ok(row) else "decision yes, checks no"


def render_table(rows: list[dict], titles: dict[str, str]) -> str:
    several = {t for t in {r["task"] for r in rows}
               if len({r.get("confirm") for r in rows if r["task"] == t}) > 1}
    lines = ["| " + " | ".join(HEAD) + " |", "|" + "---|" * len(HEAD)]
    for r in rows:
        task = titles.get(r["task"], r["task"]) + (f" (user answers {r['confirm']})" if r["task"] in several else "")
        agent = agent_text(r["agent"]) + (", trajectory reused" if r.get("reused_trajectory_from") else "")
        cells = [task, agent, r["setting"], r["checks_used"], r["checks_always"], r["decision"],
                 expected_text(r), match_text(r), latency_text(r)]
        lines.append("| " + " | ".join("" if c is None else str(c) for c in cells) + " |")
    return "\n".join(lines)


def count(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def describe(rows: list[dict], folder: Path) -> str:
    """Three sentences, every name and number from the logs."""
    metas = [meta_of(read_log(folder / r["file"])) for r in rows]
    fake = [bool(m.get("fake_monitor")) for m in metas]
    days = sorted({str(m.get("recorded_at") or "")[:10] for m in metas} - {""})
    where = sorted({str(m.get("recorded_on")) for m in metas if m.get("recorded_on")})
    own = [r for r in rows if not r.get("reused_trajectory_from")]
    groq = [r for r in own if r["agent"].startswith("groq:")]
    scripted = [r for r in own if r["agent"] == "scripted"]
    reused = len(rows) - len(own)
    tasks = len({r["task"] for r in rows})
    one = (f"The table lists {count(len(rows), 'recorded run')} of {count(tasks, 'demo task')}"
           f"{' (recorded on ' + ', '.join(where) + ', ' + ' and '.join(days) + ')' if where and days else ''}: "
           f"they are recordings, nothing here ran live, and the replay website only plays these logs back.")
    parts = []
    if groq:
        models = sorted({agent_text(r["agent"]) for r in groq})
        parts.append(f"the {' and '.join(models)} agent in {count(len(groq), 'run')}")
    if scripted:
        why = sorted({str(r.get("fallback_reason")) for r in scripted if r.get("fallback_reason")})
        parts.append(f"the scripted agent in {count(len(scripted), 'run')}" + (f" ({'; '.join(why)})" if why else ""))
    two = (f"The agent's own episodes used {' and '.join(parts)}; the other {count(reused, 'run')} (setting "
           f"`always`) started no new agent episode and replayed the agent messages of the same task's selective "
           f"run up to its first risky action, so only the monitor setting differs.")
    matched = sum(1 for r in rows if r.get("match"))
    checked = sum(1 for r in rows if checks_ok(r))
    if all(fake):
        monitor = "a rule-based FAKE monitor on CPU (not the trained model; these runs only test the website)"
    else:
        models = sorted({str(m.get("monitor_model")) for m in metas if m.get("monitor_model")})
        adapters = sorted({str(m.get("adapter_dataset")) for m in metas if m.get("adapter_dataset")})
        if adapters:        # the log's model label is "<base model>+<adapter folder on the recording machine>"
            models = sorted({m.split("+", 1)[0] for m in models})
        monitor = (" and ".join(models) or "the trained model") + \
            (f" with the adapter `{' and '.join(adapters)}`" if adapters else "")
        if any(fake):
            monitor += f" (but {count(sum(fake), 'run')} used the rule-based FAKE monitor)"
    k = sorted({r["k"] for r in rows})
    three = (f"The monitor was {monitor}, run as system {VERSION} (k = {', '.join(map(str, k))} retrieved policies): "
             f"{matched} of {count(len(rows), 'run')} gave the decision the task expects and {checked} used the "
             f"expected number of checks, and `latency` is the monitor's model time summed over its passes.")
    return " ".join([one, two, three])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", default=str(RUNS))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--allow-fake", action="store_true", help="accept fake-monitor runs (never for the report)")
    args = ap.parse_args(argv)
    folder = Path(args.runs)
    rows, problems = load(folder)
    if not rows and not problems:
        problems = [f"{folder}/summary.json lists no run"]
    if rows and not problems and not args.allow_fake and any(is_fake(r, folder) for r in rows):
        problems.append("fake-monitor runs are not report results (pass --allow-fake only to test this script)")
    if rows and not problems:
        problems += replay_check(rows, folder)
    for p in problems:
        print("PROBLEM", p)
    if problems:
        return 1
    print(f"{len(rows)} runs checked: schema, agent label, monitor {VERSION} k={VERSIONS[VERSION]['shown']}, "
          f"snapshot + diffs, summary.json = logs, replay through the website's API")
    if args.check_only:
        return 0
    titles = {t.task_id: t.title or t.task_id for t in load_tasks(TASKS)}
    text = ("# Demo runs\n\nGenerated by `python scripts/demo_table.py` from `" +
            str(folder.resolve().relative_to(ROOT) if folder.resolve().is_relative_to(ROOT) else folder.name) +
            "/summary.json` and the run logs. Do not edit by hand.\n\n" +
            render_table(rows, titles) + "\n\n" + describe(rows, folder) + "\n")
    Path(args.out).write_text(text, encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
