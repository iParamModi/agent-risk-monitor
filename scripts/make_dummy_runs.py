"""Fake runs for the 4 settings, to test the evaluation code end to end (PLAN Step 12 "dummy run").

  python scripts/make_dummy_runs.py
  python -m src.eval.tables --run never=outputs/runs/dummy_never --run always=outputs/runs/dummy_always \
      --run selective=outputs/runs/dummy_selective --run oracle=outputs/runs/dummy_oracle \
      --out outputs/runs/dummy_report --title "Dummy results (fake data)"

Shape follows the test set (decisions.md R11.2): 60 seeds, T1 24 / T2 15 / T3 6 / T4 6 / T5 9, six domains.
Each record has one "hardness" number shared by all settings, so settings make mistakes on the
same hard records, as a real model would. NOT real results.
"""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.common.io import REPO_ROOT, write_jsonl  # noqa: E402

OUT = REPO_ROOT / "outputs" / "runs"
SEED = 42
DOMAINS = ("FILE", "PRIV", "ACC", "FIN", "REPO", "CAL")
SEEDS_PER_TYPE = {"T1": 24, "T2": 15, "T3": 6, "T4": 6, "T5": 9}
RISK_BY_DOMAIN = {"FILE": "DATA_LOSS", "PRIV": "PRIVACY_LEAKAGE", "ACC": "ACCESS_CONTROL",
                  "FIN": "FINANCIAL_LOSS", "REPO": "DATA_LOSS", "CAL": "PRIVACY_LEAKAGE"}
WEAKER = {"ASK_CONFIRMATION": ["ALLOW"], "BLOCK": ["ALLOW", "ASK_CONFIRMATION"],
          "ESCALATE": ["ALLOW", "ASK_CONFIRMATION", "BLOCK"], "ALLOW": []}
# chance of a wrong decision: (check needed and the setting saw the fact, check needed and it did not, no check needed)
ERROR = {"never": (None, 0.45, 0.10), "always": (0.08, None, 0.10),
         "selective": (0.09, 0.45, 0.11), "oracle": (0.06, None, 0.08)}


def record(seed_id, domain, case_type, decision, check_needed, i, subtype=None, side=None, version=None):
    file = f"report_{i}.pdf"
    risky = decision != "ALLOW"
    return {
        "record_id": f"{seed_id}-{side or subtype or version}", "seed_id": seed_id, "domain": domain,
        "case_type": case_type, "subtype": subtype, "pair_side": side, "task": "decide_action",
        "gold": {"decision": decision, "risk_label": "UNSAFE" if risky else "SAFE",
                 "risk_type": RISK_BY_DOMAIN[domain] if risky else "NONE",
                 "check_needed": check_needed,
                 "required_checks": [{"tool": "check_file_sharing", "args": {"file": file}}] if check_needed else None},
    }


def make_records(rng: random.Random) -> list[dict]:
    recs, i = [], 0
    for case_type, n in SEEDS_PER_TYPE.items():
        for k in range(n):
            i += 1
            dom = DOMAINS[i % len(DOMAINS)]
            sid = f"IND-{dom}-{case_type}-{k + 1:03d}"
            if case_type == "T1":       # hidden fact decides; A safe, B not
                recs += [record(sid, dom, "T1", "ALLOW", True, i, side="A"),
                         record(sid, dom, "T1", rng.choice(["BLOCK", "ASK_CONFIRMATION"]), True, i, side="B")]
            elif case_type == "T2":     # a: fact already known and fresh; b-d: must check
                bad = rng.choice(["BLOCK", "ASK_CONFIRMATION"])
                recs += [record(sid, dom, "T2", bad if st == "c" else rng.choice(["ALLOW", bad]), st != "a", i, subtype=st)
                         for st in "abcd"]
            else:
                decision = {"T3": "ALLOW", "T4": "BLOCK", "T5": "ESCALATE"}[case_type]
                needs = case_type == "T5" and k % 2 == 0      # facts-disagree T5 needs checks
                recs += [record(sid, dom, case_type, decision, needs, i, version=v) for v in ("v1", "v2")]
    return recs


def predict(rec: dict, setting: str, hardness: float, rng: random.Random) -> dict:
    gold = rec["gold"]
    needed = gold["check_needed"]
    if setting == "never":
        calls, saw_fact = [], False
    elif setting == "always":
        calls, saw_fact = ([dict(c) for c in gold["required_checks"]] if needed else []) + \
                          [{"tool": "check_file_owner", "args": {"file": "x"}}, {"tool": "check_recipient_type", "args": {"recipient": "y"}}], True
    elif setting == "oracle":
        calls, saw_fact = ([dict(c) for c in gold["required_checks"]] if needed else []), True
    else:
        saw_fact = needed and rng.random() < 0.88
        calls = [dict(c) for c in gold["required_checks"]] if saw_fact else []
        if not needed and rng.random() < 0.15:
            calls = [{"tool": "check_file_owner", "args": {"file": "x"}}]
        if calls and rng.random() < 0.05:      # a bad first call, then a retry
            calls = [{"tool": "check_sharing", "args": {}, "error": "unknown_tool"}] + calls
    for c in calls:
        c.setdefault("error", None)
    seen, unseen, no_check = ERROR[setting]
    p = (seen if saw_fact else unseen) if needed else no_check
    decision = gold["decision"]
    if hardness < p:
        weaker = WEAKER[decision]
        decision = rng.choice(weaker) if weaker and rng.random() < 0.7 else \
            rng.choice([d for d in ("ALLOW", "ASK_CONFIRMATION", "BLOCK", "ESCALATE") if d != decision])
    risky = decision != "ALLOW"
    output = {"type": "DECISION", "decision": decision, "risk_label": "UNSAFE" if risky else "SAFE",
              "risk_type": (gold["risk_type"] if gold["risk_type"] != "NONE" and rng.random() < 0.8
                            else rng.choice(["SECURITY", "OTHER"])) if risky else "NONE",
              "evidence": {"facts": [], "policy_ids": []}}
    if rng.random() < 0.01:
        output = None     # invalid JSON
    passes = 1 if setting in ("never", "always", "oracle") else (2 if calls else 1)
    return {**rec, "output": output, "calls": calls, "passes": passes,
            "tokens_in": rng.randint(900, 1500) * passes + 150 * len(calls), "tokens_out": rng.randint(40, 120) * passes,
            "time_s": round(rng.uniform(0.8, 1.6) * passes, 2)}


def main() -> int:
    rng = random.Random(SEED)
    recs = make_records(rng)
    hardness = {r["record_id"]: rng.random() for r in recs}
    for setting in ("never", "always", "selective", "oracle"):
        srng = random.Random(f"{SEED}-{setting}")
        rows = [predict(r, setting, hardness[r["record_id"]], srng) for r in recs]
        write_jsonl(OUT / f"dummy_{setting}" / "predictions.jsonl", rows)
    print(f"wrote {len(recs)} fake records x 4 settings to {OUT.relative_to(REPO_ROOT)}/dummy_*/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
