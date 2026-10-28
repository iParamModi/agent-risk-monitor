# To Prateek: 🔴 HIGH PRIORITY, do first: check tools for every deciding fact, then the check gateway

From Meet, 2026-10-27. **Start here when you pull, before any other task.** Phase B fine-tuning on our records,
the oracle setting and the check metrics (check recall, correct missing fact) all wait on these two tasks, and the
submission is 30 Oct. Param's tasks (`2026-10-27_to_Param_phase_b_blockers.md`) need your task 1 first.

## 🔴 Update 2026-10-28: the gateway (task 2) is now the ONLY thing blocking Phase B

Param's tasks are done and verified (`required_checks` filled, 0 merge problems, test lock OK). The Phase B
builder's readiness check now lists one missing item: `src/gateway/gateway.py: for_record`.

### Why we cannot train without the gateway

1. **The second-pass examples need real check results.** Half of what Phase B teaches is "ask for a check, read the
   result, then decide". The result in the training prompt must be exactly what the gateway returns at evaluation
   (same fields, same values, same wording). If we wrote the results with some other code, the model would learn
   one format and see another at test time.
2. **T1 pairs cannot be learned without results.** A and B have byte-identical text and opposite gold (e.g. ALLOW vs
   BLOCK). Without a check result in the prompt, training would show the model the same input with two opposite
   answers: it learns nothing, or learns to guess.
3. **Training only first passes is worse than not training.** The model would learn to ask for checks but never to
   decide after one, so in the selective setting it would fail exactly at the step we want to measure.
4. **We cannot evaluate the fine-tuned model either.** The selective, always and oracle settings all call the
   gateway; without it only the never setting runs on our records, and the main hypothesis (selective vs always)
   cannot be tested.
5. **Time.** One Phase B run is about 5 to 6 hours on Kaggle T4 x2 and we submit on 30 Oct. The run must start as
   soon as the gateway is in, so there is time for one evaluation.

What is ready and waiting: `python -m src.training.build_sft --phase b` (builds as soon as `for_record` exists) and
`tests/test_gateway_contract.py` (4 tests: errors as data, OOD-only tools, every gold check answers with only its
`returns` fields, gold never read). Make that file pass, push, and tell Meet: Meet starts the Kaggle run.

## Where we are

- All 518 records are merged, checked, split and locked in `data/records/` (`make records`; report:
  `data/generated/reports/merge_report.json`). 0 problems in every automatic and leakage check.
- **344 records need a check** (`gold.check_needed`): train 160, val 28, test 83, OOD 73.
- For each of them the model must learn to ask for the right check (first pass: `NEED_INFORMATION` with
  `checks` = `gold.required_checks`) and then decide from the check result (second pass). That needs:
  1. a check tool that returns the deciding fact (today **115 of the 316 T1/T2 check-needed records** have a
     deciding fact that no tool in `configs/check_tools.yaml` returns), and
  2. the gateway that produces the check results (`src/gateway/` is empty).
- `python -m src.training.build_sft --phase b` (ready) stops and lists exactly these gaps until both are done.

## Task 1: finish the check tool decisions (group A + group B)

**Goal:** every deciding fact below is returned by a check tool in `configs/check_tools.yaml` (a new tool or a
field on an existing one), with its `configs/check_table.yaml` rows and the simulator field. Your group B (16
seeds) is part of this; seed changes go to Param as P0, as you planned.

Deciding facts of T1/T2 check-needed records that no check returns today (counted on `data/records/`):

| fact | records | splits | seeds | proposed tool (`check_tool_coverage.py` UNCOVERED) |
|---|---|---|---|---|
| archived | 15 | train 15 | IND-REPO-T2-001..005 | check_repository_archived |
| is_last_admin | 11 | train 11 | IND-ACC-T1-005, IND-ACC-T2-008/009/010 | check_admin_count |
| owner_approved | 6 | train 6 | IND-ACC-T1-002/007/012 | check_owner_approval |
| legal_hold | 6 | train 4, OOD 2 | IND-FILE-T1-007/015, OOD-CUST-T1-003 | check_legal_hold |
| authorized_hr, authorized_financial, authorized_pii, authorized_legal, clearance | 12 | val 4, test 4, OOD 4 | IND-ACC-T1-001/004/008/010, OOD-ACC-T1-001, OOD-CUST-T1-006 | check_user_clearance |
| address_verified | 4 | val 2, OOD 2 | IND-CAL-T1-004, OOD-CAL-T1-001 | check_recipient_verification |
| owner_team | 4 | train 4 | IND-FILE-T1-005, IND-REPO-T1-002 | check_owner_team |
| contains_pii | 4 | train 2, test 2 | IND-FILE-T1-014, IND-PRIV-T1-007 | check_file_pii |
| sanctioned | 4 | train 2, OOD 2 | IND-FIN-T1-006, OOD-FIN-T1-001 | check_sanctions |
| nda_in_place | 4 | train 2, OOD 2 | IND-PRIV-T1-008, OOD-PRIV-T1-002 | check_recipient_nda |
| backup_exists | 4 | train 2, OOD 2 | IND-REPO-T1-005, OOD-REPO-T1-001 | check_repository_backup |
| status | 3 | OOD 3 | OOD-CUST-T2-001 | check_customer_status |
| contract_active, is_backup, locked, payee_preapproved, kyc_status, dual_approval_obtained, marketing_consent | 2 each | train | IND-CAL-T1-003, IND-FILE-T1-008, IND-FILE-T1-011, IND-FIN-T1-003/004/008, IND-PRIV-T1-004 | see UNCOVERED |
| duplicate_flag, compliance_locked | 2 each | val | IND-FIN-T1-009, IND-REPO-T1-007 | see UNCOVERED |
| environment, dlp_scan, has_active_incidents, has_open_dependencies, has_active_deploys, lifecycle | 2 each | test | IND-FILE-T1-012, IND-PRIV-T1-011, IND-REPO-T1-003/004/006/008 | see UNCOVERED |
| processor_status, dnc, dispute, consent_scope | 2 each | OOD | OOD-CUST-T1-002/005/007/008 | see UNCOVERED |

**T5 facts_disagree (14 seeds, 28 records):** each needs its **two** disagreeing facts mapped to the two checks
that return them (your `T5_FIELDS`): IND-ACC-T5-001/003/005, IND-FIN-T5-001/003, IND-PRIV-T5-002 (`account_type`
vs `recipient_type`), IND-PRIV-T5-004 (`account_type` vs `recipient_class`), IND-ACC-T5-007 (`admin_count` vs
`is_last_active_admin`), IND-FILE-T5-002 (`classification` vs `sharing`), IND-FILE-T5-005 (`classification` vs
`retention`), IND-FILE-T5-006 (`locked_by_file_info` vs `locked_by_lock_check`), IND-REPO-T5-002 (`authorization`
vs `repository_status`), OOD-CUST-T5-004 (`consent_check` vs `dnc_registry`), OOD-CUST-T5-005 (`legal_hold` vs
`retention_status`).

**Done when:** `python scripts/check_tool_coverage.py` shows every in-scope seed passing (or the rest listed as
Param's seed fixes), and Param has the final map **fact → (check tool, which argument gets the resource)** for his
`required_checks` pass. Suggestion: put that map in one small file (e.g. `configs/fact_checks.yaml`) that his pass
and your coverage script both read, so the two can never disagree.

## Task 2: the check gateway, `src/gateway/gateway.py`

Already called by `src/training/build_sft.py` (Phase B) and meant for `src/monitor/loop.py`
(`run_monitor(..., gateway=...)`). The contract is a test, `tests/test_gateway_contract.py`: it is skipped now
and runs as soon as `for_record` exists.

```python
def for_record(record: dict) -> Gateway: ...      # reads record["hidden"] and record["set"] only, never gold

class Gateway:
    def call(self, tool: str, args: dict) -> dict: ...
```

1. Only tools in `configs/check_tools.yaml`; tools with `ood: true` only when `record["set"] == "ood"`.
   Anything else → `{"error": "unknown_tool", ...}` (R7.3).
2. `args` checked against `params` / `required`: missing or unknown arguments → `{"error": "invalid_args"}`.
3. A write action (any `write` tool in `configs/tool_phases.yaml`) → `{"error": "write_not_allowed"}` (R7.4).
4. A resource that is not in the record's state → `{"error": "not_found"}`.
5. A result has **only** the tool's `returns` fields, computed from `record["hidden"]["state"]` (the flat true
   state at the proposed action) and, for facts that no single entity holds (`is_last_admin`, `admin_count`),
   from `record["hidden"]["key_facts"]`. Never any other hidden field.
6. For every record, every `gold.required_checks` call answers without an error.
7. Errors are data (dicts), never exceptions: the loop counts every call (R7.6). Deterministic, no LLM.

`hidden.state` is lists of entities: `users` (user_id), `files` (file_id, folder_id), `folders` (folder_id, path),
`accounts` (account_id), `repositories` (repo_id), `contacts` (address or email), `customer_records`
(customer_id), `destinations` (address). A file without its own `sharing` takes its folder's, as in
`lma_agent/sim/readers.py`. `src/data_gen/auto_checks.py` has `find_entities` / `state_value` if you want to
reuse them.

**Done when:** `tests/test_gateway_contract.py` passes (all 4 tests run, none skipped once Param has filled
`required_checks`).

## ⚠️ Be careful (these are the ways this can go wrong)

1. **Tool descriptions reach the prompt.** `src/monitor/check_tools.py` shows every in-domain tool's name, params
   and `returns` to the model in every prompt. Keep descriptions generic: no record names or values from our
   data (no `user_23`, `org_4`, real amounts), nothing that hints at a decision.
2. **One fact per tool, and no extra fields.** A result returns only its `returns` fields, never another hidden
   fact (e.g. `check_user_clearance` must not also show `owner_approved`). An extra field is a leak: the model
   would learn facts it did not ask for.
3. **OOD-only tools stay OOD-only** (`ood: true`). The CUST tools are the `new_tools` shift of the OOD test; if an
   in-domain prompt shows them, the OOD test no longer measures that shift.
4. **The result must be the true value for that record.** T1 A and B have the same text but different hidden
   facts, so the same call answers differently on each side; T2c's `hidden.state` is already after the write.
   When a check expresses a fact in other words (`account_type: employee` → `recipient_type: internal`), use one
   mapping for every record and write it down in the fact → check map.
5. **The gateway never reads `gold`** (`tests/test_gateway_contract.py` checks this), never raises (errors are
   dicts with the exact names `unknown_tool`, `invalid_args`, `not_found`, `write_not_allowed`), and is
   deterministic. No LLM anywhere in it.
6. **Renaming an existing check** breaks `configs/check_table.yaml`, the seed notes, the coverage script and
   Param's `required_checks`. Avoid it; if you must, change all of them in one commit and tell Param.
7. **Do not edit `data/records/`, `data/LOCKED_TEST.sha256` or `data/records/splits.yaml`**, and do not edit
   records in `data/generated/` (that is Param's task 3). Seed changes go to Param.
8. **Policy ids stay hidden.** `src/monitor/prompt_builder.py` now shows policies as `[1] [2] [3]`
   (`number_policies`); keep it when you wire the gateway into the loop.
9. **Before pushing:** `python scripts/check_tool_coverage.py`, then `make test` (must pass, R13.4). Follow
   `CLAUDE.md` for the commit (PROGRESS.md, no AI attribution, no force push).

## Order and hand-off

1. You: task 1 → send Param the fact → check map. Task 2 can run in parallel.
2. Param: group-B seed fixes + regenerate the 34 records, then `gold.required_checks` for all 344 records.
3. Meet: `make records` + relock check, wire `src/monitor/run.py` for our records (retrieval + gateway), then
   Phase B on Kaggle (`build_sft --phase b`).

When each task is done: move it to Completed in `PROGRESS.md` (remove its row from the 🔴 HIGH PRIORITY table) and
tell Meet.
