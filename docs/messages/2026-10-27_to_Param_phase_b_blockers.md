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
   That is expected: run `python -m src.data_gen.split --relock`, then add a Changelog row in
   `docs/decisions.md` (R11.3: which records changed and why).
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

When each task is done: move it to Completed in `PROGRESS.md` (remove its row from the 🔴 HIGH PRIORITY table).
