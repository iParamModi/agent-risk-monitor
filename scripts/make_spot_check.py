"""Spot check of the normalized external records (DATASET.md section 2.4, step 5).

  python scripts/make_spot_check.py          writes data/external/spot_check.md
  python scripts/make_spot_check.py --tally  counts the Yes/No boxes you ticked

1. Automatic check on ALL records: every raw turn is compared with the converted turn
   (order, role, text after cleaning, action, label). The result goes at the top of the file.
2. 20 records per source (10 SAFE + 10 UNSAFE, seed 2026, at most 4,096 tokens so they fit
   on screen) are written one by one: ORIGINAL (raw JSON) then CONVERTED (our record), with a
   Yes/No box. The human reads both and ticks Yes if they say the same thing.
The file is never overwritten once a box is ticked (use --force to start again).
"""
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.common.io import REPO_ROOT, read_jsonl  # noqa: E402
from src.external.load_atbench import load_atbench  # noqa: E402
from src.external.load_rjudge import load_rjudge  # noqa: E402
from src.external.normalize import clean  # noqa: E402
from src.external.sample import load_excluded  # noqa: E402

EXT_DIR = REPO_ROOT / "data" / "external"
OUT = EXT_DIR / "spot_check.md"
SEED, PER_LABEL, MAX_TOKENS = 2026, 10, 4096
SHOW_CHARS = 1500     # longer strings are cut the same way in ORIGINAL and CONVERTED
TOOL_DESC_CHARS = 300


# ---------- automatic check ----------

def expected_rjudge(raw: dict) -> list[tuple]:
    turns = [("context", clean(raw["profile"]), None, None)]
    for t in (t for rnd in raw["contents"] for t in rnd):
        if t["role"] == "user":
            turns.append(("user", clean(t["content"]), None, None))
        elif t["role"] == "agent":
            action = t.get("action")
            turns.append(("agent", clean(t.get("thought")), None, clean(action) if action is not None else None))
        elif t.get("content") is not None:
            turns.append(("tool", clean(t["content"]), None, None))
    return turns


def expected_atbench_action(action: str) -> tuple:
    try:
        obj = json.loads(action)
        args = json.loads(obj["arguments"]) if isinstance(obj["arguments"], str) else obj["arguments"]
        if isinstance(obj.get("name"), str) and obj["name"] and isinstance(args, dict):
            return {"name": obj["name"], "args": args}, None
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
        pass
    return None, clean(action)


def expected_atbench(raw: dict) -> list[tuple]:
    turns = [("context", None, None, None)]     # tool list: checked by name below
    for t in (t for rnd in raw["contents"] for t in rnd):
        if t["role"] == "agent":
            turns.append(("agent", clean(t.get("thought")), *expected_atbench_action(t["action"])))
        else:
            turns.append(({"user": "user", "environment": "tool"}[t["role"]], clean(t["content"]), None, None))
    return turns


def compare(rec: dict, raw: dict, expected: list[tuple]) -> list[str]:
    problems = []
    if rec["gold"]["risk_label"] != ("UNSAFE" if raw["label"] == 1 else "SAFE"):
        problems.append(f"label {raw['label']} became {rec['gold']['risk_label']}")
    got = rec["visible"]["trajectory"]
    if len(got) != len(expected):
        return problems + [f"{len(expected)} turns expected, {len(got)} found"]
    for i, (msg, (role, text, call, action)) in enumerate(zip(got, expected)):
        if msg["role"] != role:
            problems.append(f"turn {i}: role {role} became {msg['role']}")
        if text is not None and msg["text"] != text:
            problems.append(f"turn {i}: text differs")
        if msg["tool_call"] != call:
            problems.append(f"turn {i}: tool_call differs")
        if msg["action_text"] != action:
            problems.append(f"turn {i}: action_text differs")
    if rec["source"] == "atbench":
        missing = [t["name"] for t in raw["tool_used"] if f"- {t['name']}" not in got[0]["text"]]
        if missing:
            problems.append(f"tools missing from context: {missing}")
    return problems


def auto_check() -> tuple[dict, dict, dict]:
    """Returns ({source: summary}, {record_id: raw}, {record_id: record})."""
    excluded = load_excluded()
    raws, recs, summary = {}, {}, {}
    sources = {
        "r_judge": ([(f"RJ-{Path(p).stem}-{r['id']}", r) for p, r in load_rjudge()], expected_rjudge),
        "atbench": ([(f"ATB-{r['id']}", r) for r in load_atbench()], expected_atbench),
    }
    for name, (pairs, expect) in sources.items():
        ours = {r["record_id"]: r for r in read_jsonl(EXT_DIR / f"{name}.jsonl")}
        bad, lost = {}, []
        for rid, raw in pairs:
            raws[rid] = raw
            if rid not in ours:
                if rid not in excluded:
                    lost.append(rid)
                continue
            recs[rid] = ours[rid]
            problems = compare(ours[rid], raw, expect(raw))
            if problems:
                bad[rid] = problems
        summary[name] = {"raw": len(pairs), "converted": len(ours), "excluded": len(pairs) - len(ours) - len(lost),
                         "lost": lost, "extra": sorted(set(ours) - {rid for rid, _ in pairs}), "mismatch": bad}
    return summary, raws, recs


# ---------- markdown ----------

def cut(obj):
    """Shortens long strings so a record fits on screen; same rule for both sides."""
    if isinstance(obj, str) and len(obj) > SHOW_CHARS:
        return obj[:1000] + f" [... {len(obj) - 1300} characters not shown ...] " + obj[-300:]
    if isinstance(obj, list):
        return [cut(x) for x in obj]
    if isinstance(obj, dict):
        return {k: cut(v) for k, v in obj.items()}
    return obj


def original_view(rec: dict, raw: dict) -> dict:
    if rec["source"] == "r_judge":    # goal is the same text in every R-Judge record
        return {k: raw[k] for k in ("id", "profile", "contents", "label")}
    tools = [{"name": t["name"], "description": (t.get("description") or "")[:TOOL_DESC_CHARS]} for t in raw["tool_used"]]
    return {"id": raw["id"], "tool_used": tools, "contents": raw["contents"], "label": raw["label"]}


def converted_view(rec: dict) -> dict:
    return {"record_id": rec["record_id"], "risk_label": rec["gold"]["risk_label"],
            "trajectory": rec["visible"]["trajectory"]}


def block(obj) -> str:
    return "```json\n" + json.dumps(cut(obj), indent=2, ensure_ascii=False) + "\n```"


def pick(recs: dict, source: str) -> list[dict]:
    rng = random.Random(SEED)
    pool = sorted((r for r in recs.values() if r["source"] == source and r["meta"]["n_tokens"] <= MAX_TOKENS),
                  key=lambda r: r["record_id"])
    out = []
    for label in ("SAFE", "UNSAFE"):
        out += rng.sample([r for r in pool if r["gold"]["risk_label"] == label], PER_LABEL)
    return sorted(out, key=lambda r: r["record_id"])


def raw_location(rec: dict) -> str:
    folder = "r_judge/data/" if rec["source"] == "r_judge" else "atbench/"
    return f"`data/raw/{folder}{rec['meta']['source_file']}`, id {rec['meta']['source_id']}"


def render(summary: dict, raws: dict, recs: dict) -> str:
    lines = [
        "# Spot check: original vs converted external records",
        "",
        "DATASET.md section 2.4 step 5. Made by `scripts/make_spot_check.py`. Checked by: Meet",
        "",
        "## How to check",
        "",
        "For each record, read **ORIGINAL** (the raw dataset file) and **CONVERTED** (our record), then tick one box.",
        "Tick **Yes** if all of these hold, otherwise tick **No** and write the problem:",
        "",
        "1. Same turns, in the same order (user, agent, tool).",
        "2. Same words. Only extra spaces and blank lines may differ.",
        "3. Right roles: `user` → user, `agent` → agent, `environment` → tool.",
        "4. Agent turn: `thought` → `text`; `action` → `action_text`, or for ATBench JSON actions → `tool_call`"
        " with the same name and arguments.",
        "5. Right label: `label` 1 → UNSAFE, 0 → SAFE.",
        "6. First converted message: R-Judge = the `profile`; ATBench = the list of tool names.",
        "",
        "Removed on purpose (not a problem): R-Judge `goal` (same in every record), environment turns that are `null`,"
        " ATBench tool descriptions cut to their first line (200 characters).",
        f"Very long strings are cut the same way on both sides (`[... N characters not shown ...]`).",
        "",
        "To tick a box, change `[ ]` to `[x]`. When done: `python scripts/make_spot_check.py --tally`.",
        "",
        "## Automatic check (all records)",
        "",
        "| Source | Raw | Converted | Excluded (physical) | Lost | Turn or label mismatches |",
        "|---|---|---|---|---|---|",
    ]
    for name, s in summary.items():
        lines.append(f"| {name} | {s['raw']} | {s['converted']} | {s['excluded']} | {len(s['lost'])} | {len(s['mismatch'])} |")
    for name, s in summary.items():
        for rid, problems in list(s["mismatch"].items())[:20]:
            lines.append(f"- {rid}: {'; '.join(problems[:3])}")
    n = 0
    for source, title in (("r_judge", "R-Judge"), ("atbench", "ATBench")):
        lines += ["", f"## {title} (20 records)"]
        for rec in pick(recs, source):
            n += 1
            rid = rec["record_id"]
            lines += [
                "", "---", "", f"### {n}. {rid}", "",
                f"ORIGINAL: {raw_location(rec)} · CONVERTED: `data/external/{source}/{rid}.json`", "",
                "**ORIGINAL**", "", block(original_view(rec, raws[rid])), "",
                "**CONVERTED**", "", block(converted_view(rec)), "",
                f"**Same?** <!-- check:{rid} -->", "", "- [ ] Yes", "- [ ] No", "",
                "Problem (if No): ",
            ]
    return "\n".join(lines) + "\n"


def tally(text: str) -> int:
    sections = re.split(r"<!-- check:(\S+) -->", text)[1:]
    yes, no, open_ = [], [], []
    for rid, body in zip(sections[::2], sections[1::2]):
        y = re.search(r"- \[[xX]\] Yes", body) is not None
        n = re.search(r"- \[[xX]\] No", body) is not None
        (open_ if y == n else yes if y else no).append(rid)
    print(f"{len(yes)} Yes, {len(no)} No, {len(open_)} not ticked (or both ticked)")
    for label, ids in (("No", no), ("Not ticked", open_)):
        if ids:
            print(f"  {label}: {', '.join(ids)}")
    return 0 if not no and not open_ else 1


def main() -> int:
    if "--tally" in sys.argv:
        return tally(OUT.read_text(encoding="utf-8"))
    if OUT.exists() and re.search(r"- \[[xX]\]", OUT.read_text(encoding="utf-8")) and "--force" not in sys.argv:
        print(f"{OUT.name} already has ticked boxes; not overwriting (use --force to start again)")
        return 1
    summary, raws, recs = auto_check()
    OUT.write_text(render(summary, raws, recs), encoding="utf-8")
    for name, s in summary.items():
        print(f"{name}: {s['converted']}/{s['raw']} converted, {s['excluded']} excluded, {len(s['lost'])} lost, "
              f"{len(s['extra'])} extra, {len(s['mismatch'])} mismatches")
    print(f"wrote {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
