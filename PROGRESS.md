# Project Progress

> Check this file before starting any work. Update it and push to GitHub after every change.
> Last updated: 2026-10-26 by Meet

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
| Step 6: policy retrieval (`src/policies/store.py`, `retriever.py`: BM25 + `bge-base-en-v1.5`, top 3; recall@3 + T5 conflict recall) | Meet | 2026-10-26 | Temporary `data/policies/policies.jsonl` built from `docs/Policy.md` (visible text only) until Param's Step 5 replaces it. Query = action + args + seed `story_hint` for now. ✅ Code + tests: `scripts/build_policies.py`, `src/policies/store.py`, `retriever.py`, `scripts/eval_retrieval.py` (recall@1/3/5, T5 conflict recall, w = 0.0…1.0, in-domain seeds only). ✅ Temp store: 138 in-domain, 152 OOD. Next: install `sentence-transformers` (CPU) and run the first report; w tuned on val seeds after Step 5 + split |
| **Monitor loop + Qwen3-8B fine-tuning** (`src/monitor/`: prompt builder, parser, 4 settings `never`/`always`/`selective`/`oracle`, gateway calls; writes `outputs/runs/<run_id>/predictions.jsonl` per `docs/evaluation_metrics.md` §2 + §8; then SFT file + QLoRA, R13.1) | Prateek, Meet | 2026-10-25 | Shared M3 work (see `decisions.md` Changelog); split of parts to agree with Meet. **Loop done (2026-10-25)**: `src/monitor/` (4 settings, strict parser, prompt builder, OpenAI-compatible model client for vLLM / hosted API, `python -m src.monitor.run`), `prompts/monitor_v1.txt`, `monitor_risk_v1.txt`; dry run on 147 external val records → `src.eval.tables` OK. Our records wait for gateway (Step 4), retrieval (Step 6), check-tool list (R7.1), check table (R7.5). Next: GPU for Qwen3-8B (R13.3), SFT file Models: prompted base Qwen3-8B + one QLoRA run. Starting with the loop |
| Step 8: in-domain seed specs (`data/seeds/in_domain/`) | Param, Moiesha | 2026-10-08 | **All 150 in-domain seeds reviewed + pushed** (T1/T4/T5 = Param 97, T2/T3 = Moiesha 53), schema-valid, 0 `reviewer: TBD`. Policies stubbed (P_*) until Step 5. **All 45 OOD seeds authored + pushed** (`data/seeds/ood/`), awaiting verification (see Next Up). Remaining Step 8: Step 9 record generation |

## Next Up

| Task | Assigned To | Depends On | Notes |
|------|-------------|------------|-------|
| **Step 5: policy store** (`data/policies/policies.jsonl`, `policy_logic.yaml`, `conflicts.yaml`, `policies_ood.jsonl`). Replace Meet's **temporary** `policies.jsonl` / `policies_ood.jsonl` (made by `scripts/build_policies.py` from `docs/Policy.md`, visible text only) | **Param** | none | Please also: (1) give all policy texts the same style: 16 start lowercase or lack a full stop (P_FILE_05, P_FILE_25, P_PRIV_05, P_PRIV_10, P_ACC_09, P_ACC_10, P_ACC_18, P_ACC_19, P_FIN_05, P_FIN_06, P_FIN_12, P_REPO_05, P_REPO_06, P_REPO_12, P_CAL_10, P_CAL_11), mostly T5 conflict rules, so the style would tell the model "conflict"; (2) OOD reworded policies reuse in-domain IDs (e.g. `P_ACC_03`) but R8.2 says `P_<DOMAIN>_<NN>_R`: pick one and keep seeds + store the same. Keep the `{"policy_id", "text"}` format so the retriever and monitor loop work unchanged |
| **R-Judge risk-type re-check (blind, NO LLM)**: run `python scripts/show_recheck.py <YourName>`, then in `data/external/risk_type_recheck.csv` fill `recheck_type` on your rows (6 classes spelled exactly, or `CONFUSED`) + `recheck_note` when hard | **Meet 57 ✅ done (2026-10-21)**, **Prateek 56 ✅ done (2026-10-24)**, **Param 49/57 (2026-10-24) + Prateek filled Param's 8 blank + 2 CONFUSED (2026-10-25)**, **Moiesha 56 done (2026-10-25)** (random split, seed 20261020; ~5 new unlabelled records each) | guide verified | **Use only `risk_type_categories.txt`. NO Claude/ChatGPT/any LLM: LLM labels are rejected and must be redone; if used, log it here and tell Prateek (CLAUDE.md §6).** Old labels + Claude suggestions removed from the sheet; do not open record JSONs, `risk_type_review.csv` or `risk_type_double_check.csv`. Save as CSV UTF-8, no sorting. **All 226 rows filled.** Next: team confirms Prateek's labels on the 2 ex-CONFUSED rows (RJ-webbrowser-135, RJ-code_agentmonitor-142), then Meet reruns `map_risk` + kappa |
| **More phase 1 seeds for thin tools**: `revoke_permission` has 2 seeds, `archive_repository` 5, `move_file` 5 (as proposed action). Aim for **≥ 8 each** (+6 / +3 / +3), spread over T1-T5 with A/B counter-direction cases like the existing ones | **Param** | seed cleanup (use the new names) | Use the names in `docs/seed_cleanup.md`. Check: `python scripts/validate_seeds.py`, `python scripts/check_seed_vocab.py` (0 problems), then `python scripts/split_by_phase.py` must show the new seeds in phase 1 |
| **Step 2: review + lock `docs/decisions.md` (v2)**: read all 15 sections (62 rules). For any change, add a row to the Changelog at the bottom with your reason. Then a 1 h team meeting on the 6 ⚠️ rules, and all four tick **Sign to lock** | **Everyone** (Meet, Param, Prateek, Moiesha) | none | Blocks configs, gold labeler and record generator. ⚠️ rules: R5.1 names = `lma_agent`'s (Param + Prateek), R7.1 first check-tool set (**Prateek**), R11.6 writer LLM, R13.2 second agent LLM, R13.3 **GPU**, R15.2 30 Oct scope |
| **Check gateway + StepLog→record converter**: monitor's read-only `check_*` tools on `lma_agent/sim/readers.py` (names/returns as in `docs/Policy.md` A + `attrs`), and `StepLog` → record trajectory + `proposed_action` | **Prateek** | seed cleanup (Param) for final check-tool names | `docs/alignment_issues.md` sections 4-5; **read `docs/evaluation_metrics.md` §2 + §8**: the format of `predictions.jsonl` (gateway calls + `error` names) that the scoring needs |
| Task agent: write the 40 live tasks (`flow_agent.md` section 7) | TBD | agent loop done | Mind the Groq limit of 8,000 tokens/min |
| **Phase 2, step 1 (start here when phase 1 works)**: phase 2 has only 4 seeds (`create_event`). Write seeds for the phase 2 tools (`pay_bill`, `search_files`, `list_repos`, `list_transactions`, `send_message`, `create_share_link`, `delete_folder`, `delete_user`, `reset_password`, `upload_file`, `cancel_event`, `forward_email`, `unshare_file`) and add those tools to the company (`lma_agent`) | TBD | phase 1 done | Tool list: `configs/tool_phases.yaml` (phase2). Retrain on `phase1_train + phase2_train` from the base model (`scripts/split_by_phase.py`) |
| Verify OOD CUST seeds (20) | Param: T1 (8), T5 (5); Moiesha: T2 (1), T3 (3), T4 (3) | seeds pushed | `data/seeds/ood/OOD-CUST-*.yaml`; set `reviewer:` to your name when done |
| Verify OOD reworded-domain seeds (25) | Param: T1 (10), T4 (2), T5 (1); Moiesha: T2 (10), T3 (2) | seeds pushed | `OOD-{FILE,PRIV,ACC,FIN,REPO,CAL}-*.yaml`; Moiesha how-to in the note below |

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
| Seed cleanup: align all 174 seeds to shared contract tool names | Param | 2026-10-25 | `scripts/gen_seeds.py`, `configs/schemas/seed.schema.json`, 150 `data/seeds/in_domain/IND-*.yaml`, 24 `data/seeds/ood/OOD-*.yaml` | Fix 1: `requested_by` moved from `proposed_action.args` to top-level field (150 seeds + gen_seeds.py + schema). Fix 2: `share_file` arg `to:`→`with:` (6 seeds), 2 T4 seeds changed to `move_file`. Fix 3: 24 OOD seeds renamed from old `lma_agent`-style names to shared contract (`grant_access`→`grant_permission`, `path`→`file`, etc.). `check_seed_vocab.py` → 0, `validate_seeds` → 195/195 |
| Step 12: evaluation code | Meet | 2026-10-25 | `src/eval/metrics.py`, `bootstrap.py`, `stats_tests.py`, `tables.py`, `scripts/make_dummy_runs.py`, `tests/test_metrics.py`, `test_bootstrap.py`, `test_stats_tests.py`, `test_tables.py`, `Makefile` | All R10 metrics, bootstrap by seed (2,000, 95% CI), R10.4 hypothesis check, Wilcoxon + exact McNemar (per record + per seed), report `outputs/tables/main.md|json`. Input = one case row per record per setting in `outputs/runs/<id>/predictions.jsonl` (format in `metrics.py`). `make eval-dummy` gives a full report on fake data. Note: with ~150 test records the Δ interval is about ±7 points, so the hypothesis can fail even when selective is only ~1 point worse |
| Step 7: external data (schema, normalize, split + sample, risk types, token counts, spot check) | Meet | 2026-10-25 | `configs/schemas/record.schema.json`, `src/external/*`, `data/external/*`, `scripts/make_spot_check.py`, `data/external/spot_check.md` | R-Judge 531 + ATBench 999 records (41 physical removed), split 70/10/20 by group, 150+150 train samples, risk types set. Token counts in `meta.n_tokens`. Spot check: automatic compare of all 1,530 records = 0 mismatches; 40 read by hand = 40 correct. Still open: apply the R-Judge re-check once the 8 blank + 2 CONFUSED rows are settled (Next Up) |
| Tool phases + seed split (phase 1 / phase 2 / ood) | Prateek | 2026-10-25 | `configs/tool_phases.yaml`, `scripts/split_by_phase.py`, `tests/test_split_by_phase.py`, `data/training/seed_phases.json`, `lma_agent/tools.yaml` (`create_event` → phase 2), `STATUS.md`, `decisions.md` | Phase 1 agent = 20 tools (9 read + 11 write). Seeds: phase 1 146, phase 2 4 (`create_event`), ood 39, rejected 6 (OOD-ACC `grant_access`, fixed by Param's cleanup). Same script splits records into `data/training/phase*_*.jsonl` once Step 9 makes them. revoke_permission has only 2 seeds |
| Demo company (`lma_agent`) changed to the seed vocabulary | Prateek | 2026-10-25 | `lma_agent/tools.yaml`, `sim/models.py`, `sim/readers.py`, `sim/seed_state.py`, `tools/read_tools.py`, `tools/write_tools.py`, `tasks/smoke_tasks.yaml`, `tests/agent/*`, `decisions.md`, `scripts/check_seed_vocab.py` | 14 actions with seed names/args (`grant_permission`, `file`, `with`, `amount_inr`, ...) + new `move_file`, `edit_file`, `archive_repository`, `create_event`; folders with inherited sharing (`internal`/`public`/`external:<org>`), `restricted`, hidden `attrs` for the ~80 seed facts. 113 agent tests pass (+ a test that fails if company and seed list drift). Live Groq smoke: 7/7 done, 0 errors, calls in seed format |
| ATBench misinformation-harm re-check (25 used records, blind, by hand) | Meet | 2026-10-24 | `data/external/atbench_h5_recheck.csv`, `atbench.jsonl` | decisions.md R3.6: labelled one by one with the guide (no LLM); applied by `map_risk` over the map default |
| R-Judge agreement Prateek vs Moiesha (30-row blind check) | Meet | 2026-10-20 | `data/labels/kappa_report.json`, `src/external/map_risk.py` | 26 comparable rows (4 were removed physical records): agreement 69%, Cohen's kappa 0.57 < 0.6, so the guided blind re-check was started |
| Risk-type guide verified + R-Judge re-check sheet made blind | Prateek | 2026-10-20 | `data/external/risk_type_categories.txt`, `risk_type_recheck.csv`, `scripts/show_recheck.py`, `src/external/map_risk.py`, `tests/test_map_risk.py`, `CLAUDE.md` | Guide FINAL (rules + decision order + tricky pairs). 226 rows randomly re-split (stratified by split/new). Sheet now has no `current_type`/`claude_suggestion` columns; `show_recheck.py` hides gold. `map_risk` treats `CONFUSED` as no label. No-LLM labelling rule added (CLAUDE.md §6) |
| Step 2: `docs/decisions.md` draft for review | Meet | 2026-10-19 | `docs/decisions.md` | 51 rules with recommended answers (PLAN Step 2 + 17 open issues + alignment, models, roles, 30 Oct scope); not locked yet |
| Step 8: OOD seeds authored (45 = 20 CUST + 25 reworded-domain) | Param | 2026-10-19 | `data/seeds/ood/*.yaml` (45) | All schema-valid (195/195). CUST = new domain (archive_record/export_customer_data; consent/retention/legal-hold facts; P_CUST_* policies). Reworded = 6 old domains, same policy logic/new wording+style+values; T2 staled via the real tools `share_file`/`transfer_money`. Type mix T1 18 / T2 11 / T3 5 / T4 5 / T5 6 = 112 records. `reviewer: TBD` pending verification (see Next Up) |
| R-Judge blind double check (30 rows) | Prateek | 2026-10-20 | `data/external/risk_type_double_check.csv` | All 30 `reviewer_b_type` filled blind (`risk_type_review.csv` not opened). PRIVACY_LEAKAGE 11, OTHER 8, SECURITY 5, ACCESS_CONTROL 3, FINANCIAL_LOSS 2, DATA_LOSS 1. Ready for Meet to compute agreement with Moiesha |
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

- Risk-type labels must be human-only (no LLM). Any LLM use on labels: log it here and tell Prateek
- Seeds (training) and `lma_agent` (demo) use different action names, args and fact values. Must be aligned before Step 9, or the trained monitor won't work in the demo. Owners: Prateek + Param. Details: `docs/alignment_issues.md`
- Long ATBench records are almost all UNSAFE: over 4,096 tokens = 51 UNSAFE / 5 SAFE, over 8,192 = 36 UNSAFE / 0 SAFE (longest 100,824, raw HTML pages in tool outputs). Dropping them (PLAN Step 16) shifts the label balance and lets the model learn "long = unsafe". Team to decide: drop, or shorten very long tool outputs. Details: `data/external/token_report.json`
- Test size vs the main hypothesis: on dummy data with ~150 test records, the 95% interval of Δ unsafe rate is about ±7 points, so the hypothesis can fail even when selective is only ~1 point worse than always. Decide at the meeting, before locking the test set: more test seeds, or OOD records as a second check. Details: `docs/evaluation_metrics.md` §6
- Agent LLM is now `openai/gpt-oss-120b` (not Llama 3.3 70B). PLAN Step 22 needs a second agent LLM from another family, still to pick

## Activity Log (newest first)

- 2026-10-25, Prateek: labelled Param's 8 blank + 2 CONFUSED R-Judge re-check rows by hand with the guide (no LLM; labels typed in a local text file, copied into the sheet by script, format checked). Re-check sheet now 226/226; 2 ex-CONFUSED rows to confirm at the meeting
- 2026-10-26, Meet: retrieval code (BM25 + bge-base-en-v1.5, w-weighted, top 3) + tests; temporary `data/policies/policies.jsonl` (138) + `policies_ood.jsonl` (152) from `docs/Policy.md` for Param to replace in Step 5
- 2026-10-26, Meet: started Step 6 (policy retrieval)
- 2026-10-25, Prateek: monitor loop `src/monitor/` (never/always/selective/oracle, R9 limits, strict JSON, writes `predictions.jsonl` in the eval format); 22 new tests, 244 pass
- 2026-10-25, Param: seed cleanup done — all 174 seeds aligned to shared contract tool names (Fix 1-3 from `docs/seed_cleanup.md`); `check_seed_vocab.py` → 0, `validate_seeds` → 195/195; merge conflicts with Prateek's reviewer updates resolved (kept `reviewer: Moiesha`)
- 2026-10-25, Prateek: monitor loop + Qwen3-8B fine-tuning now shared by Prateek and Meet (includes the `predictions.jsonl` output); Prateek starts with the loop
- 2026-10-25, Meet: assigned Prateek to follow `docs/evaluation_metrics.md` for the `predictions.jsonl` output; added test-size question to Blockers
- 2026-10-25, Meet: `docs/evaluation_metrics.md`: how every metric and test is computed, the `predictions.jsonl` input format, how to run; Prateek to follow §2 + §8 for the monitor loop and gateway
- 2026-10-25, Meet: Step 12 completed: `src/eval/tables.py` report + `make eval-dummy` (fake runs for 4 settings → full report); 37 eval tests
- 2026-10-25, Meet: `src/eval/stats_tests.py`: Wilcoxon on checks per case and exact McNemar on correctness (R10.4), per record and per seed
- 2026-10-25, Meet: `src/eval/bootstrap.py`: bootstrap by seed (2,000 resamples, 95% CI), paired differences between settings, R10.4 hypothesis check
- 2026-10-25, Meet: `src/eval/metrics.py`: every R10 metric (unsafe-action, wrong-block, check precision/recall, missing fact, savings, F1s, pair + T2 accuracy, call quality) with hand-checked tests; invalid output counts as wrong (R9.6)
- 2026-10-25, Meet: started Step 12 (evaluation code)
- 2026-10-25, Meet: Step 7 completed. Spot check: all 1,530 external records match the raw files automatically (0 mismatches), 40 read by hand (20 per source) all correct (`data/external/spot_check.md`)
- 2026-10-25, Prateek: assigned Param more seeds for revoke_permission / archive_repository / move_file; added phase 2 start task to Next Up
- 2026-10-25, Moiesha: finished blind R-Judge re-check of own 56 rows by hand using the guide (no LLM); format checked
- 2026-10-25, Moiesha: verified 11 OOD seeds (7 CUST, 4 ACC)
- 2026-10-25, Meet: format fix in `risk_type_recheck.csv`: removed a duplicate header line (from Param's save) that made `map_risk` fail; no label changed. Re-check: 162/226 filled (Moiesha 0/56, Param 8 blank)
- 2026-10-25, Prateek: split tools and seeds into phase 1 / phase 2 (`configs/tool_phases.yaml`, `scripts/split_by_phase.py`); phase 1 = 20 tools, 146 in-domain seeds
- 2026-10-25, Prateek: demo company `lma_agent` now uses the seed vocabulary (actions, args, folders, fact values, hidden attrs); 113 tests pass, live smoke 7/7
- 2026-10-24, Prateek: wrote seed cleanup guide (`docs/seed_cleanup.md`) + checker (`scripts/check_seed_vocab.py`); assigned seed cleanup to Param
- 2026-10-24, Prateek: started aligning `lma_agent` with the seed vocabulary (company follows seeds)
- 2026-10-24, Meet: Qwen3 token counts for all external records (`src/external/count_tokens.py`, `make external` step). R-Judge median 406 / max 1,444; ATBench median 1,304 / p95 4,509 / max 100,824 (56 over 4,096, 36 over 8,192, nearly all UNSAFE; see Blockers)
- 2026-10-24, Meet: `docs/decisions.md` v2 ready for sign-off (clean rule file, 62 rules, 6 need the meeting; R14.1: datasets not in git; R3.6 settled per record)
- 2026-10-24, Prateek: finished blind R-Judge re-check of own 56 rows by hand using the guide (no LLM); format checked
- 2026-10-24, Meet: labelled the 25 ATBench misinformation-harm records by hand (no LLM) and applied them
- 2026-10-24, Meet: added blind per-record re-check for the 25 used ATBench misinformation-harm records (`atbench_h5_recheck.csv`, `scripts/show_atbench_recheck.py`); `map_risk` applies it
- 2026-10-24, Param: filled recheck_type for 49 of 57 assigned rows in `data/external/risk_type_recheck.csv`; 2 rows marked CONFUSED (RJ-webbrowser-135: OTHER vs SECURITY; RJ-code_agentmonitor-142: PRIVACY_LEAKAGE vs SECURITY); 8 rows left blank (unsure — rows: RJ-trafficdispatch-128, RJ-terminal-0, RJ-software-10, RJ-socialapp-112, RJ-software-55, RJ-socialapp-104, RJ-moneymanagement-18, RJ-ds_app-2132); CONFUSED + blank rows flagged for Prateek to settle
- 2026-10-21, Meet: finished blind R-Judge re-check of own 57 rows by hand using the guide (no LLM); format checked
- 2026-10-20, Meet: marked R-Judge agreement task completed (kappa 0.57, see `data/labels/kappa_report.json`)
- 2026-10-20, Prateek: verified risk-type guide; re-check rows randomly split over 4 people and made blind (LLM suggestions + old labels removed, `scripts/show_recheck.py`); no-LLM labelling rule in CLAUDE.md §6
- 2026-10-20, Meet: removed 41 physical-world external records (`excluded_physical.txt`), split unchanged; applied Moiesha's R-Judge types; blind check kappa 0.57; wrote risk-type guide (`risk_type_categories.txt`) and 4-person re-check sheet (`risk_type_recheck.csv`)
- 2026-10-20, Prateek: finished R-Judge blind double check (30/30 rows in `risk_type_double_check.csv`); handed to Meet for agreement
- 2026-10-19, Meet: `docs/decisions.md` draft ready for team review (51 rules, 8 need discussion)
- 2026-10-19, Meet: started Step 2 draft (`docs/decisions.md`)
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
