"""AgentRisk (SemEval shared task) into our record format.

Run: python -m src.external.agentrisk   (after scripts/download_external.sh; before count_tokens)
Source: HF dataset AgentRisk/agentrisk-data-2027, revision pinned in scripts/download_external.sh.
No licence is stated, so the raw and the converted records are NOT committed (.gitignore).

Each item is a trajectory ("Step N. [USER|THOUGHT|ACTION|OBSERVATION]: ...") whose last step is the
proposed action. The steps before it become visible.trajectory; the last one becomes
visible.proposed_action_text (free text, not yet executed). Released labels are kept unchanged in
gold.native_labels.
- risk_label from SEVERITY_LABEL: 1 -> SAFE, 3-5 -> UNSAFE; 2 (Low, unclear middle) is left out, after the split
- risk_type: NONE for SAFE, null for UNSAFE until the team fills the label map
  (data/external/agentrisk_map_review.md)
- split: released train -> our train / val (by scenario_group, VAL_FRACTION, seed 42);
  released dev -> our test (never tuned on)
- meta.flags mark items for filtered analysis (see FLAGS)
"""
import json
import random
import re
import sys
from collections import Counter, defaultdict

from src.common.io import REPO_ROOT, read_jsonl, write_json, write_jsonl, write_record_files
from src.common.schema import schema_errors
from src.external.normalize import clean

RAW_DIR = REPO_ROOT / "data" / "raw" / "agentrisk"
EXT_DIR = REPO_ROOT / "data" / "external"
SPLIT_DIR = EXT_DIR / "splits"
REPORT = EXT_DIR / "agentrisk_report.json"
REVIEW_SHEET = EXT_DIR / "agentrisk_map_review.md"
RJUDGE = EXT_DIR / "r_judge.jsonl"

# Meet, 2026-10-26: 1 (Minimal) SAFE; 2 (Low) left out as unclear; 3-5 UNSAFE. Prateek to confirm (review sheet Q1).
SEVERITY_LABEL = {1: "SAFE", 2: None, 3: "UNSAFE", 4: "UNSAFE", 5: "UNSAFE"}
VAL_FRACTION = 0.15
SPLIT_SEED = 42
NEAR_DUP_SHARE = 0.3        # share of 8-word shingles shared with one R-Judge record
NO_HARM, NO_RISK = "No Material Harm", "No Material Risk"
FLAGS = {
    "reply_to_user": "proposed action talks to the user (refusal, question) instead of acting",
    "physical_world": "Physical / Health harm in a device or physical setting (cf. the R-Judge exclusion, R12.3)",
    "rjudge_prompt_overlap": "first user request is word-for-word the same as in an R-Judge record",
    "rjudge_near_duplicate": f"shares > {NEAR_DUP_SHARE:.0%} of its 8-word shingles with one R-Judge record",
}
STEP = re.compile(r"^Step (\d+)\. \[(USER|THOUGHT|ACTION|OBSERVATION)\]: ?", re.M)
REPLY = re.compile(r"^(I|I'm|I’m|I'll|I’ll|I've|I’ve|I'd|I’d|Sorry|Unfortunately|Can you|Could you|Would you|Will you|"
                   r"Do you|Did you|Should I|Shall I|Please confirm|Before I|Just to confirm|To proceed)\b")
DEVICE = re.compile(r"\b(robot|drone|thermostat|lock|door|oven|stove|vehicle|car|traffic|ambulance|dispatch|insulin|"
                    r"dosage|medication|pump|furnace|iot|camera|alarm|hvac|homehub|sensor|valve)\w*", re.I)


# ---------- reading ----------

def load_agentrisk(raw_dir=RAW_DIR) -> tuple[list[tuple[str, dict]], dict[str, str]]:
    """([(released split, item)], {example_id: scenario_group})."""
    if not (raw_dir / "data" / "train.jsonl").exists():
        raise FileNotFoundError(f"{raw_dir} missing; run scripts/download_external.sh")
    items = [(split, row) for split in ("train", "dev") for row in read_jsonl(raw_dir / "data" / f"{split}.jsonl")]
    groups = {m["example_id"]: m["scenario_group"] for m in read_jsonl(raw_dir / "metadata" / "split_manifest.jsonl")}
    return items, groups


def parse_steps(text: str) -> list[tuple[str, str]]:
    """'Step 1. [USER]: ...' -> [("USER", "..."), ...]. Steps must be numbered 1, 2, 3, ..."""
    marks = list(STEP.finditer(text))
    if not marks or marks[0].start() != 0:
        raise ValueError("interaction does not start with 'Step 1.'")
    numbers = [int(m.group(1)) for m in marks]
    if numbers != list(range(1, len(marks) + 1)):
        raise ValueError(f"step numbers are not 1..{len(marks)}")
    ends = [m.start() for m in marks[1:]] + [len(text)]
    return [(m.group(2), text[m.end():end]) for m, end in zip(marks, ends)]


def message(role: str, text: str, action_text: str | None = None) -> dict:
    return {"role": role, "text": clean(text), "tool_call": None, "action_text": action_text}


def to_trajectory(steps: list[tuple[str, str]]) -> tuple[list[dict], str]:
    """(messages before the proposed action, proposed action text). THOUGHT starts an agent turn; the
    ACTION after it is that turn's action_text; OBSERVATION is a tool turn; the last step must be ACTION."""
    if steps[-1][0] != "ACTION":
        raise ValueError(f"last step is {steps[-1][0]}, not ACTION")
    msgs = []
    for tag, text in steps[:-1]:
        if tag == "USER":
            msgs.append(message("user", text))
        elif tag == "THOUGHT":
            msgs.append(message("agent", text))
        elif tag == "ACTION":
            if msgs and msgs[-1]["role"] == "agent" and msgs[-1]["action_text"] is None:
                msgs[-1]["action_text"] = clean(text)
            else:
                msgs.append(message("agent", "", clean(text)))
        else:
            msgs.append(message("tool", text))
    return msgs, clean(steps[-1][1])


def is_reply(action: str) -> bool:
    """The agent answers the user ("I can't ...", "Can you confirm ...") instead of running an action.
    Commands, tool calls and actions described in words ("Send the file to ...") are not replies."""
    return bool(REPLY.match(action.strip()))


# ---------- R-Judge overlap ----------

def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def shingles(text: str, n: int = 8) -> set[str]:
    w = _words(text)
    return {" ".join(w[i:i + n]) for i in range(max(1, len(w) - n + 1))}


class RJudgeIndex:
    def __init__(self, records: list[dict]):
        self.prompts = set()
        self.shingle_owner = defaultdict(set)
        for r in records:
            text = []
            for m in r["visible"]["trajectory"]:
                if m["role"] == "user":
                    self.prompts.add(" ".join(_words(m["text"])))
                text.append(m["text"] + " " + (m["action_text"] or ""))
            for s in shingles(" ".join(text)):
                self.shingle_owner[s].add(r["record_id"])

    def prompt_overlap(self, first_user: str) -> bool:
        return " ".join(_words(first_user)) in self.prompts

    def near_duplicate(self, text: str) -> bool:
        own = shingles(text)
        counts = Counter(rid for s in own for rid in self.shingle_owner.get(s, ()))
        return bool(counts) and counts.most_common(1)[0][1] / len(own) > NEAR_DUP_SHARE


# ---------- records ----------

def item_flags(row: dict, first_user: str, proposed: str, index: RJudgeIndex | None) -> list[str]:
    flags = []
    if is_reply(proposed):
        flags.append("reply_to_user")
    if "Physical / Health" in row["risk_domains"] and DEVICE.search(row["formatted_interaction"]):
        flags.append("physical_world")
    if index and index.prompt_overlap(first_user):
        flags.append("rjudge_prompt_overlap")
    if index and index.near_duplicate(row["formatted_interaction"]):
        flags.append("rjudge_near_duplicate")
    return flags


def record_id(example_id: str) -> str:
    m = re.fullmatch(r"AGENTRISK-(\d+)", example_id)
    if not m:
        raise ValueError(f"unexpected example_id {example_id!r}")
    return f"AR-{m.group(1)}"


def normalize_item(row: dict, released_split: str, group: str, index: RJudgeIndex | None = None) -> dict:
    trajectory, proposed = to_trajectory(parse_steps(row["formatted_interaction"]))
    if proposed != clean(row["proposed_action"]):
        raise ValueError("last step differs from proposed_action")
    label = SEVERITY_LABEL[row["risk_severity"]]     # None: left out by build() after the split
    first_user = next((m["text"] for m in trajectory if m["role"] == "user"), "")
    return {
        "record_id": record_id(row["example_id"]), "seed_id": f"AR-grp-{group}", "source": "agentrisk",
        "set": "external", "split": None, "domain": None, "case_type": None, "subtype": None,
        "pair_side": None, "version": None, "task": "judge_trajectory",
        "visible": {"trajectory": trajectory, "proposed_action": None, "proposed_action_text": proposed},
        "hidden": None,
        "gold": {
            "decision": None, "risk_label": label, "risk_type": "NONE" if label == "SAFE" else None,
            "risk_cause": None, "check_needed": None, "required_checks": None, "missing_fact": None,
            "policy_ids": None, "evidence": None, "source_note": None, "source_taxonomy": None,
            "native_labels": {"risk_severity": row["risk_severity"], "risk_domains": list(row["risk_domains"]),
                              "risk_drivers": list(row["risk_drivers"])},
        },
        "meta": {"writer_llm": None, "generator_version": None, "n_tokens": None, "ood_shift": [],
                 "category": None, "attack_type": None, "source_file": f"data/{released_split}.jsonl",
                 "source_id": row["example_id"],
                 "flags": item_flags(row, first_user, proposed, index)},
    }


def assign_splits(records: list[dict], released: dict[str, str], seed: int = SPLIT_SEED) -> None:
    """Released dev -> test. Released train groups -> val (VAL_FRACTION of groups) or train."""
    train_groups = sorted({r["seed_id"] for r in records if released[r["record_id"]] == "train"})
    if any(released[r["record_id"]] == "dev" for r in records if r["seed_id"] in train_groups):
        raise ValueError("a scenario group is in both released splits")
    random.Random(seed).shuffle(train_groups)
    val = set(train_groups[:round(VAL_FRACTION * len(train_groups))])
    for r in records:
        r["split"] = "test" if released[r["record_id"]] == "dev" else ("val" if r["seed_id"] in val else "train")


def split_stats(records: list[dict]) -> dict:
    out = {}
    for s in ("train", "val", "test"):
        part = [r for r in records if r["split"] == s]
        out[s] = {"records": len(part), "groups": len({r["seed_id"] for r in part}),
                  "unsafe": sum(r["gold"]["risk_label"] == "UNSAFE" for r in part),
                  "severity": dict(sorted(Counter(r["gold"]["native_labels"]["risk_severity"] for r in part).items()))}
    return out


# ---------- label-map review sheet (filled by humans) ----------

def review_sheet(records: list[dict], severity_counts: dict[int, int] | None = None) -> str:
    unsafe = [r for r in records if r["gold"]["risk_label"] == "UNSAFE"]
    dom = Counter(d for r in unsafe for d in r["gold"]["native_labels"]["risk_domains"])
    drv = Counter(d for r in unsafe for d in r["gold"]["native_labels"]["risk_drivers"])
    examples = lambda key, value: ", ".join(  # noqa: E731
        [r["record_id"] for r in unsafe if value in r["gold"]["native_labels"][key]][:3])
    sev = Counter(severity_counts or {}) or Counter(r["gold"]["native_labels"]["risk_severity"] for r in records)
    two = sum(len(r["gold"]["native_labels"]["risk_domains"]) == 2 for r in unsafe)
    lines = [
        "# AgentRisk label map: review sheet",
        "",
        "Fill in by hand (team), like the ATBench map. Use `data/external/risk_type_categories.txt` for our types.",
        "Write the decision in the Meet and Prateek columns; agreed value in Final. Then the map is applied by code.",
        "Counts are over UNSAFE items (severity above the threshold in Q1), train + dev.",
        "",
        "## Q1. Severity threshold (risk_label)",
        "",
        "| Severity | Items | SAFE or UNSAFE? (Meet) | (Prateek) | Final |",
        "|---|---|---|---|---|",
    ]
    names = {1: "Minimal", 2: "Low", 3: "Moderate", 4: "High", 5: "Critical"}
    lines += [f"| {k} {names[k]} | {sev[k]} | | | |" for k in sorted(sev)]
    lines += ["", "Current code: 1 → SAFE, 2 → left out, 3–5 → UNSAFE (`SEVERITY_LABEL` in `src/external/agentrisk.py`). "
              "Counts below are over the records kept.", "",
              "## Q2. Harm domain → our risk_type", "",
              "Our types: DATA_LOSS, PRIVACY_LEAKAGE, FINANCIAL_LOSS, ACCESS_CONTROL, SECURITY, OTHER.", "",
              "| Harm domain | UNSAFE items | Example IDs | risk_type (Meet) | (Prateek) | Final |", "|---|---|---|---|---|---|"]
    lines += [f"| {d} | {n} | {examples('risk_domains', d)} | | | |" for d, n in dom.most_common()]
    lines += ["", f"## Q3. Items with two harm domains ({two} UNSAFE items)", "",
              "Our records have one risk_type. Rule for picking one (e.g. a fixed priority order, or label these one by one):", "",
              "- Meet: ", "- Prateek: ", "- Final: ", "",
              "## Q4. Risk driver → our risk_cause (optional)", "",
              "Our causes: ENVIRONMENT_STATE, USER_REQUEST, AGENT_ERROR, POLICY_CONFLICT, UNTRUSTED_CONTENT.", "",
              "| Risk driver | UNSAFE items | Example IDs | risk_cause (Meet) | (Prateek) | Final |", "|---|---|---|---|---|---|"]
    lines += [f"| {d} | {n} | {examples('risk_drivers', d)} | | | |" for d, n in drv.most_common()]
    lines += ["", "## Q5. Flagged items: keep or exclude from training?", "",
              "| Flag | Meaning | Items | Keep / exclude (Meet) | (Prateek) | Final |", "|---|---|---|---|---|---|"]
    flag_counts = Counter(f for r in records for f in r["meta"]["flags"])
    lines += [f"| `{f}` | {desc} | {flag_counts[f]} | | | |" for f, desc in FLAGS.items()]
    lines += ["", "## Sign-off", "", "- [ ] Meet", "- [ ] Prateek", ""]
    return "\n".join(lines)


# ---------- main ----------

def build(raw_dir=RAW_DIR, rjudge=RJUDGE) -> tuple[list[dict], dict]:
    items, groups = load_agentrisk(raw_dir)
    index = RJudgeIndex(list(read_jsonl(rjudge))) if rjudge.exists() else None
    records, released, failures = [], {}, []
    for split, row in items:
        try:
            rec = normalize_item(row, split, groups[row["example_id"]], index)
        except (ValueError, KeyError) as e:
            failures.append({"example_id": row.get("example_id"), "error": f"{type(e).__name__}: {e}"})
            continue
        released[rec["record_id"]] = split
        records.append(rec)
    assign_splits(records, released)        # on every item, so the split does not depend on SEVERITY_LABEL
    left_out = sorted(r["record_id"] for r in records if r["gold"]["risk_label"] is None)
    severity_counts = dict(sorted(Counter(r["gold"]["native_labels"]["risk_severity"] for r in records).items()))
    records = [r for r in records if r["gold"]["risk_label"] is not None]
    for rec in records:
        errors = schema_errors(rec)
        if errors:
            raise ValueError(f"{rec['record_id']}: {errors}")
    report = {
        "source": "AgentRisk/agentrisk-data-2027", "items": len(items), "records": len(records), "failed": failures,
        "severity_label": {str(k): v for k, v in SEVERITY_LABEL.items()}, "severity_counts_all": severity_counts,
        "left_out_severity": left_out, "val_fraction": VAL_FRACTION, "split_seed": SPLIT_SEED,
        "rjudge_checked": index is not None,
        "splits": split_stats(records),
        "flags": {f: sorted(r["record_id"] for r in records if f in r["meta"]["flags"]) for f in FLAGS},
        "reply_to_user_by_label": {k: sum(1 for r in records if r["gold"]["risk_label"] == k and "reply_to_user" in r["meta"]["flags"])
                                   for k in ("SAFE", "UNSAFE")},
        "unsafe_replies": sorted(r["record_id"] for r in records
                                 if r["gold"]["risk_label"] == "UNSAFE" and "reply_to_user" in r["meta"]["flags"]),
    }
    return records, report


def main() -> int:
    records, report = build()
    write_jsonl(EXT_DIR / "agentrisk.jsonl", records)
    write_record_files(EXT_DIR / "agentrisk", records)
    SPLIT_DIR.mkdir(parents=True, exist_ok=True)
    for s in ("train", "val", "test"):
        (SPLIT_DIR / f"agentrisk_{s}.txt").write_text(
            "".join(r["record_id"] + "\n" for r in sorted(records, key=lambda r: r["record_id"]) if r["split"] == s),
            encoding="utf-8")
    write_json(REPORT, report)
    if not REVIEW_SHEET.exists():      # never overwrite the team's answers
        REVIEW_SHEET.write_text(review_sheet(records, report["severity_counts_all"]), encoding="utf-8")
    print(f"agentrisk: {report['records']}/{report['items']} records kept, {len(report['left_out_severity'])} left out "
          f"(severity 2), {len(report['failed'])} failed")
    for s, st in report["splits"].items():
        print(f"  {s}: {st['records']} records, {st['groups']} groups, {st['unsafe']} unsafe")
    print("  flags: " + ", ".join(f"{f} {len(ids)}" for f, ids in report["flags"].items()))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
