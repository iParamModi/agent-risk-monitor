# To Param: 🔴 HIGH PRIORITY, do first: group-B seed fixes + regenerate, then `gold.required_checks` (D4)

From Meet, 2026-10-27. **Start here when you pull, before any other task.** Phase B fine-tuning on our records,
the oracle setting and the check metrics all wait on these, and the submission is 30 Oct. Both tasks need
Prateek's check tool decisions (`2026-10-27_to_Prateek_phase_b_blockers.md`, task 1) first.

## Where we are (the merge is done, you do not need to do it)

- `make records` merged all three chunks into `data/records/`: 518 records, 0 problems in every automatic check
  (`src/data_gen/auto_checks.py`) and the T1 A/B check (80/80 pairs). Reports: `data/generated/reports/`.
- Your chunk changed in one place only: `gold.native_labels: null` was added (Prateek's and Meet's have it).
- Split 60/10/30 by seed, seeds that share a gold policy kept together; `data/records/splits.yaml` is sticky
  (seeds keep their split on every rerun). `test.jsonl` + `ood_test.jsonl` are locked in `data/LOCKED_TEST.sha256`.
- **`data/generated/` stays the source.** Edit records there, never in `data/records/` (it is rebuilt).

## Task 1: Prateek's group-B seed fixes (P0), then regenerate their 34 records

Seeds (from Prateek's In Progress note): IND-FILE-T1-008/012, IND-FIN-T1-003/004/008/009,
IND-PRIV-T1-004/011, IND-REPO-T1-003/004/006/008, OOD-CUST-T1-002/005/007, OOD-CUST-T2-001.

1. Apply Prateek's seed changes, then regenerate those records with the `docs/seed_to_record.md` §10 playbook
   (same record ids, same fixed values; `writer_llm` = your session's model).
2. Run `make records`. The merge must print **0 problems** (it runs every check; problems are listed one per
   line, the full report is `data/generated/reports/merge_report.json`).
3. 10 of the 16 seeds are in test or OOD, so the split step stops with *"the locked test files would change"*.
   That is expected: check with `python scripts/changed_records.py` that only the 34 records changed (⚠️ 6
   below), run `python -m src.data_gen.split --relock`, then add a Changelog row in `docs/decisions.md`
   (R11.3: which records changed and why).
4. Commit `data/generated/`, `data/records/`, `data/LOCKED_TEST.sha256`, `data/generated/reports/` and the
   Changelog together, and tell Meet.

## Task 2: `gold.required_checks` for every check-needed record (seed_to_record.md D4)

All 518 records have `required_checks: null` today. **344 need a check** (train 160, val 28, test 83, OOD 73).

- **What:** the 1 or 2 checks that return the deciding fact(s), exactly as the monitor should ask for them:
  `[{"tool": "<check tool>", "args": {"<param>": "<value>"}}]`
  - T1 and T2 b/c/d: one check, for the key fact in `hidden.key_facts` / `missing_fact`.
  - T5 facts_disagree: the two checks whose results disagree.
  - T2a, T3, T4, T5 policy_conflict: stay `null` (no check needed).
- **Tool and args:** the tool from Prateek's final fact → check map; `args` are that tool's required `params`
  in `configs/check_tools.yaml`, filled with the resource name exactly as the record writes it (the gateway
  looks it up by that name).
- **By code, never by hand** (DATASET.md §5: code decides, humans check): a small script over
  `data/generated/` that reads the map, so the same rule fills all 344 records.
- **How it is scored:** "correct missing fact" = same tool and every gold argument with the same value; the
  oracle setting runs exactly these checks.
- **Checked for you:** the merge now validates every filled `required_checks` (tool exists, OOD-only tools only
  on OOD records, required args present and no unknown ones, only on check-needed records).

**Done when:** `make records` shows 0 problems and `"required_checks_missing": 0` (printed, and in
`merge_report.json`); then `split --relock` + a Changelog row (the test records change), commit as in task 1,
and tell Meet. After that `python -m src.training.build_sft --phase b` and `tests/test_gateway_contract.py` can
run, and Meet starts Phase B on Kaggle.

## ⚠️ Be careful (these are the ways this can go wrong)

1. **Edit only `data/generated/` and the seeds.** Never hand-edit `data/records/`: `make records` rebuilds it, and
   `tests/test_records.py` fails on a record that breaks a rule.
2. **Keep every record id**, and never delete or rename a record: the merge checks that every seed has exactly
   its variants (A/B, a-d, v1/v2).
3. **Regenerated records follow the §10 rules, the same as the first round:** no em dash; T1 A and B
   byte-identical text; v1/v2 the same gold labels; no hidden value in user or agent text; a T1 agent never reads
   the deciding fact; every action argument has a visible source; the trajectory ends on an agent turn; gold
   from `policy_logic.yaml` + `conflicts.yaml` + the trust rule, never from judgment.
4. **`hidden.state` in your own flat format** (variant values set on the entities; `key_facts` must equal what
   the state says). The merge checks this for every record.
5. **`make records` must show 0 problems.** If a check fails, fix the record or the seed. Never weaken a check
   to make it pass.
6. **Relock only what you meant to change.** Before `python -m src.data_gen.split --relock`, run
   `python scripts/changed_records.py`: it lists every changed record and field. For task 1 only the 34
   regenerated records may appear; for task 2 only `gold.required_checks`. Anything else: stop and look.
7. **Never `split --reassign`, and never move a seed in `splits.yaml`.** If the split stops with "must share a
   split", a seed fix made a seed share a gold policy with a seed in another split: stop and tell Meet.
8. **No tuning on test.** 10 of the 16 group-B seeds are test/OOD: change them only as far as Prateek's decision
   needs, with no other wording edits to test or OOD records (R11.3).
9. **`required_checks` by code from Prateek's map, never by hand or by an LLM.** Tool and argument names exactly
   as in `configs/check_tools.yaml`, resource names exactly as the record writes them, 1 check for T1/T2 b-d, 2
   for T5 facts_disagree, `null` for the rest.
10. **Commit together** `data/generated/`, `data/records/`, `data/LOCKED_TEST.sha256`, `data/generated/reports/`,
    the Changelog row and `PROGRESS.md`, following `CLAUDE.md` (no AI attribution, no force push), then tell
    Meet.

When each task is done: move it to Completed in `PROGRESS.md` (remove its row from the 🔴 HIGH PRIORITY table).
