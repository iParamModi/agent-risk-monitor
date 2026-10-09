# Project Progress

> Check this file before starting any work. Update it and push to GitHub after every change.
> Last updated: 2026-10-08 by Param

## Team

| Name | Role / Area |
|------|-------------|
| Prateek | |
| Param | |
| Meet | |
| Moiesha | |

## In Progress (currently running)

| Task | Who | Started | Status / Notes |
|------|-----|---------|----------------|
| Step 7: external data (record schema, normalize R-Judge + ATBench, split, sample, risk types) | Meet | 2026-10-07 | Done: schema, normalize, split + sample, ATBench risk types, R-Judge LLM suggestions (237 records). Next: human review of R-Judge types, token counts, spot check |
| Step 8: in-domain seed specs (`data/seeds/in_domain/`) | Param | 2026-10-08 | All 150 seeds generated, schema-valid. Policies stubbed (P_*) until Step 5. **All T1 (60) reviewed + pushed.** **T2-T5 (90) now pushed as NOT-reviewed (`reviewer: TBD`) for the team to review** + `docs/Policy.md` (the consistent policy/permission catalogue) pushed. Generators `scripts/gen_seeds.py` + `gen_policy.py` pushed |

## Next Up

| Task | Assigned To | Depends On | Notes |
|------|-------------|------------|-------|
| R-Judge risk types: fill `human_final` in `data/external/risk_type_review.csv` (237 rows, low/medium confidence first) | Meet | none | Leave `human_final` = suggestion if you agree; set `changed` = yes and a note if not |
| R-Judge blind double check: fill `reviewer_b_type` in `data/external/risk_type_double_check.csv` (30 rows) | Prateek | none | Do NOT open `risk_type_review.csv` first; read each record file and pick one type |
| Verify T2 + T3 seeds (`data/seeds/in_domain/IND-*-T2-*.yaml`, `*-T3-*.yaml`) | Moiesha | Step 8 T1 | Pushed but NOT reviewed (`reviewer: TBD`). Check each against `docs/Policy.md` (policy intent + expected gold in each seed's `notes`); set `reviewer: Moiesha` when OK. T2 = 4-subtype trust-rule cases; T3 = clearly-safe/ALLOW |
| Verify T4 + T5 seeds | (unassigned) | Step 8 T1 | Pushed, `reviewer: TBD`. T4 = clearly-unsafe/BLOCK; T5 = conflict/facts-disagree/ESCALATE |
| Step 2: lock all definitions (`docs/decisions.md` + configs) | Everyone (M1 writes) | none | Resolve the 17 open issues in PLAN.md; pick writer LLM + 2 agent LLMs; assign M1-M4 roles |

## Completed

| Task | Done By | Date | Files Changed | Notes |
|------|---------|------|---------------|-------|
| Step 8: in-domain T1 seeds (60, all 6 domains) authored + reviewed | Param | 2026-10-09 | `data/seeds/in_domain/IND-*-T1-*.yaml` (60), `configs/schemas/seed.schema.json`, `scripts/validate_seeds.py` | Hidden-state pairs; distinct policy/fact per seed, counter-direction cases so no value→label shortcut; expected gold in each `notes`. Policy IDs stubbed pending Step 5. T2-T5 (90 seeds) + `docs/Policy.md` + generators held local until reviewed |
| ATBench risk-type map (review + apply) | Meet, Prateek | 2026-10-08 | `data/external/risk_type_map_review.md`, `risk_type_map.yaml`, `src/external/map_risk.py`, `atbench.jsonl` | 497 unsafe: SECURITY 198, PRIVACY_LEAKAGE 124, OTHER 82, ACCESS_CONTROL 48, FINANCIAL_LOSS 45 |
| Step 1: repo skeleton (folders, stubs, Makefile, .gitignore, README) | Meet | 2026-10-07 | all of `STRUCTURE.md` tree, `docs/` | Still to do: Python 3.11 env, pin `requirements.txt`, real tests so `make test` passes |
| Download raw R-Judge + ATBench (part of Step 7) | Meet | 2026-10-07 | `scripts/download_external.sh`, `data/raw/` | Counts match DATASET.md: R-Judge 571 (270 safe / 301 unsafe), ATBench 1,000 (503 / 497). Run `make external` |

## Blockers / Questions

- <anything stuck or needing a team decision>

## Activity Log (newest first)

- 2026-10-10, Param: pushed T2-T5 (90 seeds, `reviewer: TBD`) + `docs/Policy.md` + generators for team review; assigned T2/T3 verification to Moiesha
- 2026-10-09, Param: reviewed + pushed all T1 seeds (60, 6 domains); diversified facts + counter-direction cases; `docs/Policy.md` catalogue drafted (held). T2-T5 under review
- 2026-10-08, Param: reviewed + pushed FILE-domain T1 seeds (14); seed schema + validator added. Other seeds held local pending review
- 2026-10-08, Meet: Claude suggested risk types for 237 used unsafe R-Judge records (`risk_type_review.csv`); 30-item blind double-check sheet for Prateek
- 2026-10-08, Meet: ATBench risk-type map signed off (Meet + Prateek) and applied to all 497 unsafe records
- 2026-10-08, Meet: ATBench risk-type review sheet added and reviewed by Meet; Prateek is Reviewer 2
- 2026-10-08, Param: started Step 8, drafting FILE-domain seed specs (one per case type T1-T5) for review
- 2026-10-08, Meet: split external data by group. R-Judge 396/58/117 (seed 56), ATBench 700/100/200 (seed 44); 300-record train samples saved
- 2026-10-08, Meet: pushed normalized external data (`data/external/`: 571 R-Judge + 1,000 ATBench records, jsonl + one file per record). `split` and UNSAFE `risk_type` still null
- 2026-10-08, Meet: normalizer also writes one readable JSON file per record (`data/external/r_judge/`, `data/external/atbench/`)
- 2026-10-08, Meet: record schema (`configs/schemas/record.schema.json`) + R-Judge/ATBench normalizer with tests
- 2026-10-07, Meet: started Step 7 (external data)
- 2026-10-07, Meet: repo skeleton set up, raw R-Judge + ATBench downloaded and pushed
