# Project Progress

> Check this file before starting any work. Update it and push to GitHub after every change.
> Last updated: 2026-10-08 by Meet

## Team

| Name | Role / Area |
|------|-------------|
| Prateek | |
| Param | |
| Meet | |

## In Progress (currently running)

| Task | Who | Started | Status / Notes |
|------|-----|---------|----------------|
| Step 7: external data (record schema, normalize R-Judge + ATBench, split, sample, risk types) | Meet | 2026-10-07 | Done: record schema + normalize (571 + 1,000 records, 0 schema errors, `make external`). Next: split + 300 sample, then risk types |

## Next Up

| Task | Assigned To | Depends On | Notes |
|------|-------------|------------|-------|
| Step 2: lock all definitions (`docs/decisions.md` + configs) | Everyone (M1 writes) | none | Resolve the 17 open issues in PLAN.md; pick writer LLM + 2 agent LLMs; assign M1-M4 roles |

## Completed

| Task | Done By | Date | Files Changed | Notes |
|------|---------|------|---------------|-------|
| Step 1: repo skeleton (folders, stubs, Makefile, .gitignore, README) | Meet | 2026-10-07 | all of `STRUCTURE.md` tree, `docs/` | Still to do: Python 3.11 env, pin `requirements.txt`, real tests so `make test` passes |
| Download raw R-Judge + ATBench (part of Step 7) | Meet | 2026-10-07 | `scripts/download_external.sh`, `data/raw/` | Counts match DATASET.md: R-Judge 571 (270 safe / 301 unsafe), ATBench 1,000 (503 / 497). Run `make external` |

## Blockers / Questions

- <anything stuck or needing a team decision>

## Activity Log (newest first)

- 2026-10-08, Meet: normalizer also writes one readable JSON file per record (`data/external/r_judge/`, `data/external/atbench/`)
- 2026-10-08, Meet: record schema (`configs/schemas/record.schema.json`) + R-Judge/ATBench normalizer with tests
- 2026-10-07, Meet: started Step 7 (external data)
- 2026-10-07, Meet: repo skeleton set up, raw R-Judge + ATBench downloaded and pushed
