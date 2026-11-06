"""Inject distractor turns into ~30% of train T1 pairs to break the "error -> UNSAFE" shortcut
(configs/distractors.yaml; docs/reports/shortcut_check.md; decisions.md 2026-11-06).

For each selected train T1 seed, the SAME distractor block (agent read on an unrelated resource -> an error /
junk / injection tool result -> the agent dismisses it) is inserted after the first user turn of BOTH the A and
the B record. A and B carry opposite gold labels, so the distractor then appears once on a SAFE record and once on
an UNSAFE one and no longer predicts the label. Gold, hidden state and the proposed action are untouched.

TRAIN RECORDS ONLY. Selection is deterministic (seed 42), stratified by domain (~30% per domain). Idempotent: a
record that already has its template's lead line is skipped. Run:  python scripts/inject_distractors.py
"""
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "data" / "generated" / "T1"
SEED = 42
FRACTION = 0.30


def agent(text, tool_call=None):
    return {"role": "agent", "text": text, "tool_call": tool_call, "action_text": None}


def tool(text):
    return {"role": "tool", "text": text, "tool_call": None, "action_text": None}


def block(t):
    return [agent(t["lead"], {"name": t["tool_call"]["name"], "args": t["tool_call"]["args"]}),
            tool(t["result"]), agent(t["dismiss"])]


def first_user_index(traj):
    for i, m in enumerate(traj):
        if m["role"] == "user":
            return i
    return -1


def inject(record, t):
    traj = record["visible"]["trajectory"]
    if any((m.get("text") or "") == t["lead"] for m in traj):
        return False                       # already injected (idempotent)
    i = first_user_index(traj)
    record["visible"]["trajectory"] = traj[:i + 1] + block(t) + traj[i + 1:]
    return True


def main():
    templates = yaml.safe_load((ROOT / "configs" / "distractors.yaml").read_text(encoding="utf-8"))["templates"]
    splits = yaml.safe_load((ROOT / "data" / "records" / "splits.yaml").read_text(encoding="utf-8"))
    t1 = sorted(s for s in splits["train"] if "-T1-" in s)
    by_dom = defaultdict(list)
    for s in t1:
        by_dom[s.split("-")[1]].append(s)

    rng = random.Random(SEED)
    selected = []
    for dom in sorted(by_dom):
        seeds = sorted(by_dom[dom])
        k = round(FRACTION * len(seeds))
        selected += rng.sample(seeds, k)
    selected = sorted(selected)

    touched, cues = [], Counter()
    for n, sid in enumerate(selected):
        t = templates[n % len(templates)]
        done = 0
        for side in ("A", "B"):
            p = GEN / f"{sid}-{side}.json"
            rec = json.loads(p.read_text(encoding="utf-8"))
            if inject(rec, t):
                p.write_text(json.dumps(rec, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
                done += 1
        if done:
            touched.append((sid, t["id"], t["cue_type"]))
            cues[t["cue_type"]] += 1

    print(f"selected {len(selected)} train T1 pairs ({FRACTION:.0%}), {2 * len(touched)} records injected")
    for sid, tid, cue in touched:
        print(f"  {sid}: {tid} ({cue})")
    print("cue types:", dict(cues))


if __name__ == "__main__":
    main()
