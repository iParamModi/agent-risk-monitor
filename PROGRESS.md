# Project Progress

> Check this file before starting any work. Update it and push to GitHub after every change.
> Last updated: 2026-10-08 by Param

## Team

| Name | Role / Area |
|------|-------------|
| Prateek | |
| Param | |
| Meet | |

## In Progress (currently running)

| Task | Who | Started | Status / Notes |
|------|-----|---------|----------------|
| Step 7: external data (record schema, normalize R-Judge + ATBench, split, sample, risk types) | Meet | 2026-10-07 | Done: schema, normalize, split + 150/150 train sample. ATBench risk-type map: Meet reviewed, waiting for Prateek (`data/external/risk_type_map_review.md`). Next: R-Judge risk types (LLM + human), token counts |
| Step 8: in-domain seed specs (FILE domain, `data/seeds/in_domain/`) | Param | 2026-10-08 | Drafting seeds ahead of Steps 2/5; `gold_policy_ids` are stubbed (P_FILE_*) until policies are written. Adding `configs/schemas/seed.schema.json` + validator. Starting with 1 seed per case type (T1-T5) |

## Next Up

| Task | Assigned To | Depends On | Notes |
|------|-------------|------------|-------|
| Review ATBench risk-type map as Reviewer 2: tick boxes in `data/external/risk_type_map_review.md`, then fill the Final table with Meet | Prateek | none (Meet's review is done) | Do not change Meet's ticks; add comments where you disagree |
| Step 2: lock all definitions (`docs/decisions.md` + configs) | Everyone (M1 writes) | none | Resolve the 17 open issues in PLAN.md; pick writer LLM + 2 agent LLMs; assign M1-M4 roles |

## Completed

| Task | Done By | Date | Files Changed | Notes |
|------|---------|------|---------------|-------|
| Step 1: repo skeleton (folders, stubs, Makefile, .gitignore, README) | Meet | 2026-10-07 | all of `STRUCTURE.md` tree, `docs/` | Still to do: Python 3.11 env, pin `requirements.txt`, real tests so `make test` passes |
| Download raw R-Judge + ATBench (part of Step 7) | Meet | 2026-10-07 | `scripts/download_external.sh`, `data/raw/` | Counts match DATASET.md: R-Judge 571 (270 safe / 301 unsafe), ATBench 1,000 (503 / 497). Run `make external` |

## Blockers / Questions

- <anything stuck or needing a team decision>

## Activity Log (newest first)

- 2026-10-08, Meet: ATBench risk-type review sheet added and reviewed by Meet; Prateek is Reviewer 2
- 2026-10-08, Param: started Step 8, drafting FILE-domain seed specs (one per case type T1-T5) for review
- 2026-10-08, Meet: split external data by group. R-Judge 396/58/117 (seed 56), ATBench 700/100/200 (seed 44); 300-record train samples saved
- 2026-10-08, Meet: pushed normalized external data (`data/external/`: 571 R-Judge + 1,000 ATBench records, jsonl + one file per record). `split` and UNSAFE `risk_type` still null
- 2026-10-08, Meet: normalizer also writes one readable JSON file per record (`data/external/r_judge/`, `data/external/atbench/`)
- 2026-10-08, Meet: record schema (`configs/schemas/record.schema.json`) + R-Judge/ATBench normalizer with tests
- 2026-10-07, Meet: started Step 7 (external data)
- 2026-10-07, Meet: repo skeleton set up, raw R-Judge + ATBench downloaded and pushed
