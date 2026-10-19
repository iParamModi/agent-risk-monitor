# Project Progress

> Check this file before starting any work. Update it and push to GitHub after every change.
> Last updated: 2026-10-19 by Param

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
| Step 7: external data (record schema, normalize R-Judge + ATBench, split, sample, risk types) | Meet | 2026-10-07 | Done: schema, normalize, split + sample, ATBench risk types, R-Judge LLM suggestions (237 records). R-Judge human review handed to Moiesha (2026-10-12). Meet next: token counts, spot check |
| Step 8: in-domain seed specs (`data/seeds/in_domain/`) | Param, Moiesha | 2026-10-08 | **All 150 in-domain seeds reviewed + pushed** (T1/T4/T5 = Param 97, T2/T3 = Moiesha 53), schema-valid, 0 `reviewer: TBD`. Policies stubbed (P_*) until Step 5. **All 45 OOD seeds authored + pushed** (`data/seeds/ood/`), awaiting verification (see Next Up). Remaining Step 8: Step 9 record generation |
| R-Judge blind double check: fill `reviewer_b_type` in `data/external/risk_type_double_check.csv` (30 rows) | Prateek | 2026-10-19 | Started, going record by record. Row 3 `record_id` typo: says RJ-bitcoint-131, file/description are RJ-bitcoin-31 (told Meet) |

## Next Up

| Task | Assigned To | Depends On | Notes |
|------|-------------|------------|-------|
| **Align training data with the demo company**: one shared action/argument/check-tool list (`configs/tools.yaml`, `configs/check_table.yaml`), then rename seeds or `lma_agent` to match; folders + folder-inherited sharing in `lma_agent/sim`; check gateway + StepLog→record converter | **Prateek + Param** | none | **Read `docs/alignment_issues.md`.** 7 of 12 seed actions missing in `lma_agent`, args and sharing values differ. Do before Step 9 record generation |
| Task agent: write the 40 live tasks (`flow_agent.md` section 7) | TBD | agent loop done | Mind the Groq limit of 8,000 tokens/min |
| Verify OOD CUST seeds (20) | Param: T1 (8), T5 (5); Moiesha: T2 (1), T3 (3), T4 (3) | seeds pushed | `data/seeds/ood/OOD-CUST-*.yaml`; set `reviewer:` to your name when done |
| Verify OOD reworded-domain seeds (25) | Param: T1 (10), T4 (2), T5 (1); Moiesha: T2 (10), T3 (2) | seeds pushed | `OOD-{FILE,PRIV,ACC,FIN,REPO,CAL}-*.yaml`; Moiesha how-to in the note below |
| Step 2: lock all definitions (`docs/decisions.md` + configs) | Everyone (M1 writes) | none | Resolve the 17 open issues in PLAN.md; pick writer LLM + 2 agent LLMs; assign M1-M4 roles |

### How to verify — OOD reworded-domain seeds (Moiesha: T2, T3)

Each reworded OOD seed is a copy of an existing in-domain rule in new words. To verify one:

1. **Find its twin.** The `gold_policy_ids` in the OOD seed is the same ID as an in-domain seed (e.g. `OOD-ACC-T2-001` uses `P_ACC_21`; compare with the in-domain `P_ACC_21` seed and the row in `docs/Policy.md`).
2. **Same logic?** Check the deciding fact, the action, and the gold decision match the original rule. The *rule* must be identical — only the surface changes.
3. **Different wording?** The policy text in `notes`, the `story_hint`, the `writer_style`, the file paths/IDs/amounts must all read differently from the in-domain twin. If it looks like a near-copy of the original wording, flag it (that defeats the OOD test).
4. **So: "same rule, different clothes."** Similar example, genuinely different wording/style/values → OK. Different rule, or identical wording → FIX.
5. Set `reviewer: Moiesha` when a seed passes.

## Completed

| Task | Done By | Date | Files Changed | Notes |
|------|---------|------|---------------|-------|
| Step 8: OOD seeds authored (45 = 20 CUST + 25 reworded-domain) | Param | 2026-10-19 | `data/seeds/ood/*.yaml` (45) | All schema-valid (195/195). CUST = new domain (archive_record/export_customer_data; consent/retention/legal-hold facts; P_CUST_* policies). Reworded = 6 old domains, same policy logic/new wording+style+values; T2 staled via the real tools `share_file`/`transfer_money`. Type mix T1 18 / T2 11 / T3 5 / T4 5 / T5 6 = 112 records. `reviewer: TBD` pending verification (see Next Up) |
| Task agent loop phase 1 (`lma_agent/`, steps 1-14 of `flow_agent.md`) | Prateek | 2026-10-19 | `lma_agent/` (sim, tools, agent, tasks, scripts), `tests/agent/`, `STATUS.md`, `decisions.md`, `flow_agent.md`, `requirements.txt` | 143 offline tests pass. Live on Groq `openai/gpt-oss-120b` (Llama 3.3 70B not available): 7/7 smoke tasks done; block/ask/escalate gates behave as designed; expected tools 6/7. Results in `STATUS.md` |
| R-Judge risk-type review (237 rows) | Moiesha | 2026-10-15 | `data/external/risk_type_review.csv` (237) | Reviewed all 237 unsafe R-Judge records (4 low, 50 med, 183 high confidence). 233 accepted suggestions, 4 overrides. Breakdown: PRIVACY_LEAKAGE 103, SECURITY 53, OTHER 37, FINANCIAL_LOSS 17, ACCESS_CONTROL 15, DATA_LOSS 12. Handed to Meet for jsonl sync & Prateek double-check. |
| Step 8: in-domain T4 (15) + T5 (22) seeds reviewed | Param | 2026-10-12 | `data/seeds/in_domain/IND-*-T4-*.yaml` (15), `*-T5-*.yaml` (22) | T4 = clearly-unsafe/BLOCK (violation visible, no check); T5 = policy_conflict + facts_disagree/ESCALATE. All `reviewer: Param`. **All 150 in-domain seeds now reviewed (0 TBD).** |
| Step 8: in-domain T3 seeds (15, all 6 domains) reviewed + diversified | Moiesha | 2026-10-11 | `data/seeds/in_domain/IND-*-T3-*.yaml` (15) | Verified clearly-safe/ALLOW rules; fixed 002 owner overlap; diversified FIN company accounts; fixed FILE 003 destination folder; all reviewer: Moiesha |
| Step 8: in-domain T2 seeds (38, all 6 domains) reviewed + diversified | Moiesha | 2026-10-10 | `data/seeds/in_domain/IND-*-T2-*.yaml` (38) | Verified 4-subtype trust rules; diversified roles/folders; fixed 005 folder mismatch bug; all reviewer: Moiesha |
| Step 8: in-domain T1 seeds (60, all 6 domains) authored + reviewed | Param | 2026-10-09 | `data/seeds/in_domain/IND-*-T1-*.yaml` (60), `configs/schemas/seed.schema.json`, `scripts/validate_seeds.py` | Hidden-state pairs; distinct policy/fact per seed, counter-direction cases so no value→label shortcut; expected gold in each `notes`. Policy IDs stubbed pending Step 5. T2-T5 (90 seeds) + `docs/Policy.md` + generators held local until reviewed |
| ATBench risk-type map (review + apply) | Meet, Prateek | 2026-10-08 | `data/external/risk_type_map_review.md`, `risk_type_map.yaml`, `src/external/map_risk.py`, `atbench.jsonl` | 497 unsafe: SECURITY 198, PRIVACY_LEAKAGE 124, OTHER 82, ACCESS_CONTROL 48, FINANCIAL_LOSS 45 |
| Step 1: repo skeleton (folders, stubs, Makefile, .gitignore, README) | Meet | 2026-10-07 | all of `STRUCTURE.md` tree, `docs/` | Still to do: Python 3.11 env, pin `requirements.txt`, real tests so `make test` passes |
| Download raw R-Judge + ATBench (part of Step 7) | Meet | 2026-10-07 | `scripts/download_external.sh`, `data/raw/` | Counts match DATASET.md: R-Judge 571 (270 safe / 301 unsafe), ATBench 1,000 (503 / 497). Run `make external` |

## Blockers / Questions

- Seeds (training) and `lma_agent` (demo) use different action names, args and fact values. Must be aligned before Step 9, or the trained monitor won't work in the demo. Owners: Prateek + Param. Details: `docs/alignment_issues.md`
- Agent LLM is now `openai/gpt-oss-120b` (not Llama 3.3 70B). PLAN Step 22 needs a second agent LLM from another family, still to pick

## Activity Log (newest first)

- 2026-10-19, Meet: listed seed vs `lma_agent` mismatches in `docs/alignment_issues.md`; assigned alignment to Prateek + Param
- 2026-10-19, Param: pushed 45 OOD seeds to `data/seeds/ood/` (20 CUST new-domain + 25 reworded-old-domain), all schema-valid; verification split assigned — CUST: Param T1/T5, Moiesha T2/T3/T4; reworded: Param T1/T4/T5, Moiesha T2/T3 (how-to in Next Up)
- 2026-10-19, Prateek: task agent loop live on Groq; agent model switched to `openai/gpt-oss-120b` (Llama 3.3 70B not on Groq); 7/7 smoke tasks done, all 4 gate branches verified
- 2026-10-19, Prateek: built task agent loop `lma_agent/` (simulator, 21 phase-1 tools, Groq client, gates, loop, smoke runner) per `flow_agent.md`; 143 tests pass offline; live Groq run pending a key
- 2026-10-15, Moiesha: completed R-Judge risk-type review (237 records in `data/external/risk_type_review.csv`); 233 accepted suggestions, 4 overrides; ready for Meet to map to `r_judge.jsonl`
- 2026-10-12, Param: robustness-checked all 150 in-domain seeds (0 issues). Fixed 3 FIN seeds (T1-005, T5-001, T5-003) where `key_fact`/the authorization check pointed at a vendor name that was only an account's `owner` label (not a modelled entity) — repointed to the account (`acct_77`/`acct_79`) so the simulator can resolve it; decisions unchanged
- 2026-10-12, Param: reviewed T4 (15) + T5 (22) in-domain seeds; all 150 in-domain seeds now reviewed (0 `reviewer: TBD`); extended gen_seeds REVIEWED guard to all cells
- 2026-10-12, Meet: handed R-Judge risk-type review to Moiesha; instructions in `data/external/risk_type_review_HOWTO.md`
- 2026-10-11, Moiesha: reviewed and diversified all in-domain T3 seeds (15, 6 domains); fixed ACC-002 ownership bug, diversified FIN accounts, fixed FILE-003 destination folder, set reviewer: Moiesha
- 2026-10-10, Moiesha: reviewed and diversified all in-domain T2 seeds (38, 6 domains); verified 4-subtype trust rules, diversified roles/folders, set reviewer: Moiesha
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
