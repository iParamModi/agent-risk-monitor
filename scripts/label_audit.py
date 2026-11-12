"""Label audit by code (no LLM, no human judgement): are the gold labels of our records consistent?

It does NOT replace the human agreement study (PLAN Step 10, decisions.md R4.5): it only finds contradictions that
code can see. It never says which label is right; anything it lists is for a person to read.

  1. merge checks (src.data_gen.merge, run without writing): schema, fixed fields, coverage, T1 pair identity
  2. rebuild: data/generated rebuilt by the merge equals the committed data/records (labels, states, visible part)
  3. lock: test.jsonl and ood_test.jsonl match data/LOCKED_TEST.sha256
  4. near-duplicates across splits (src.data_gen.dedup)
  5. decidable: two records of one seed with different gold decisions must differ in what a monitor can see
     (conversation + results of the gold checks through the gateway)
  6. same rule, same answer: T1 records with the same policies, action, deciding fact and fact value have one decision
  7. gold checks run: every gold required check returns a result without an error
  8. policy logic (scripts/check_tool_coverage.py, item 11): seed gold vs the decision the policy rules give

    python scripts/label_audit.py      # -> docs/reports/label_audit.md
"""
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.common.io import read_jsonl  # noqa: E402
from src.data_gen import merge as M  # noqa: E402
from src.data_gen.dedup import similar_pairs  # noqa: E402
from src.data_gen.split import read_lock, sha256  # noqa: E402
from src.gateway.gateway import for_record, run_oracle  # noqa: E402

OUT = ROOT / "docs" / "reports" / "label_audit.md"
FILES = {"train": "train", "val": "val", "test": "test", "ood": "ood_test"}
SKIP = {"call_id"}


def records() -> list[dict]:
    out = []
    for split, name in FILES.items():
        for r in read_jsonl(ROOT / "data" / "records" / f"{name}.jsonl"):
            if r.get("task", "decide_action") == "decide_action":
                out.append(dict(r, _split=split))
    return out


def oracle_view(r: dict) -> tuple[str, list[str], list[str]]:
    calls = run_oracle(for_record(r, setting="oracle"), r)
    results = [json.dumps({k: v for k, v in c["result"].items() if k not in SKIP}, sort_keys=True) for c in calls]
    errors = [c["tool"] for c in calls if c["result"].get("error")]
    return json.dumps(r["visible"], sort_keys=True), results, errors


def main() -> int:
    rows, md = records(), []
    seeds = M.load_seeds()
    stores = {"in_domain": {p["policy_id"] for p in M.load_policies(M.IN_DOMAIN)},
              "ood": {p["policy_id"] for p in M.load_policies(M.OOD)}}
    merged, report, _ = M.merge(M.load_generated(), seeds, None, stores, M.read_tool_names(), M.load_check_specs())
    committed = {r["record_id"]: r for f in ("all_in_domain", "all_ood")
                 for r in read_jsonl(ROOT / "data" / "records" / f"{f}.jsonl")}
    drop = ("split", "meta")
    differ = [r["record_id"] for r in merged if {k: v for k, v in r.items() if k not in drop}
              != {k: v for k, v in committed.get(r["record_id"], {}).items() if k not in drop}]
    lock = {name: sha256(ROOT / "data" / "records" / Path(name).name) == h for name, h in read_lock().items()}
    dups = similar_pairs(rows)

    views, by_seed, gold_errors = {}, defaultdict(list), []
    for r in rows:
        views[r["record_id"]] = oracle_view(r)
        by_seed[r["seed_id"]].append(r)
        if views[r["record_id"]][2]:
            gold_errors.append(f"{r['record_id']}: {views[r['record_id']][2]}")
    undecidable = []
    for seed, rs in by_seed.items():
        for i, a in enumerate(rs):
            for b in rs[i + 1:]:
                if a["gold"]["decision"] != b["gold"]["decision"] and views[a["record_id"]][:2] == views[b["record_id"]][:2]:
                    undecidable.append(f"{a['record_id']} ({a['_split']}, {a['gold']['decision']}) vs {b['record_id']} "
                                       f"({b['gold']['decision']}), required checks: {len(a['gold']['required_checks'] or [])}")
    groups = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["case_type"] != "T1":
            continue
        for key, value in (r["hidden"].get("key_facts") or {}).items():
            k = (tuple(sorted(r["gold"]["policy_ids"])), r["visible"]["proposed_action"]["name"], key.split(".")[-1],
                 json.dumps(value))
            groups[k][r["gold"]["decision"]].append(r["record_id"])
    clash = [f"{k}: {dict(v)}" for k, v in groups.items() if len(v) > 1]

    cov = subprocess.run([sys.executable, "scripts/check_tool_coverage.py"], cwd=ROOT, capture_output=True, text=True)
    cov_line = (cov.stdout.strip().splitlines() or ["(no output)"])[0]
    cov_md = (ROOT / "docs" / "check_tools_coverage.md").read_text(encoding="utf-8").split("## 5. Gold mismatches")[1]
    mismatch = [line for line in cov_md.split("\n## ")[0].splitlines()
                if line.startswith("| ") and "seed gold or policy logic" in line]

    def res(ok: bool, n: str) -> str:
        return f"pass ({n})" if ok else f"**{n}**"
    md += ["# Label audit by code", "",
           "Checks that code can make on the gold labels of our records (no LLM, no human judgement). It does not replace "
           "the human agreement study (PLAN Step 10, decisions.md R4.5, not done): it finds contradictions, it never says "
           "which label is right. Built by `scripts/label_audit.py`.", "",
           f"{len(rows)} decide_action records (train, val, test, OOD).", "",
           "| # | Check | Result |", "|---|---|---|",
           f"| 1 | Merge checks (schema, fields, coverage, T1 pair identity) | {res(not report['problems'], str(len(report['problems'])) + ' problems')}; "
           f"{len(report['flags'])} wording flags for a human; {report['t1_pairs_failed']} T1 pairs failed |",
           f"| 2 | Records rebuilt from `data/generated` equal the committed ones | {res(not differ, str(len(differ)) + ' differ')} |",
           f"| 3 | Test and OOD match the lock | {res(all(lock.values()), ', '.join(f'{Path(k).name} ' + ('OK' if v else 'MISMATCH') for k, v in lock.items()))} |",
           f"| 4 | Near-duplicates across records (dedup threshold) | {res(not dups, str(len(dups)) + ' pairs')} |",
           f"| 5 | Records of one seed with different decisions differ in what a monitor sees | {res(not undecidable, str(len(undecidable)) + ' pairs look the same')} |",
           f"| 6 | T1: same policies, action, fact and value give one decision | {res(not clash, f'{len(groups)} groups, {len(clash)} with two decisions')} |",
           f"| 7 | Every gold check runs without an error | {res(not gold_errors, str(len(gold_errors)) + ' errors')} |",
           f"| 8 | Seed gold equals the decision of the policy rules | {res(not mismatch, str(len(mismatch)) + ' seed(s) differ')} |", ""]
    if undecidable:
        md += ["**Check 5, pairs that look the same:**", "", *[f"- {x}" for x in undecidable],
               "", "(Records with 0 required checks are phase-2 create_event records, left out of training and evaluation.)", ""]
    if clash:
        md += ["**Check 6:**", "", *[f"- {x}" for x in clash], ""]
    if gold_errors:
        md += ["**Check 7:**", "", *[f"- {x}" for x in gold_errors], ""]
    if mismatch:
        md += ["**Check 8, for a person to read** (the coverage script cannot evaluate a condition that is \"visible in the "
               "action\" and assumes the rule fires; it lists the seed, not a verdict):", "",
               "| seed id | variant | fact value | seed gold | gold from policies | policies involved | note |",
               "|---|---|---|---|---|---|---|", *mismatch, ""]
    md += [f"Coverage script: `{cov_line}`. Its other failing items are seed *notes* that name a check differently from "
           "the records (the records' gold checks run and return the deciding fact, checks 5 and 7).", ""]
    OUT.write_text("\n".join(md), encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
