# To Meet: T5 facts_disagree seeds are made (from Param, 2026-11-06)

Done with the extra T5 "facts disagree" seeds. **21 new seeds, 42 records**, all two-check facts_disagree. No new tools or policies invented, everything reuses the existing check tools and policies.

## ⚠️ Read first: the locked test set changed
I added **13 test seeds (26 records)**, so I ran `split --relock`. **`test.jsonl` grew from 124 to 150 records; `LOCKED_TEST.sha256` was rewritten.** `scripts/changed_records.py` shows **42 additions and nothing else**: the original **120 phase-1 test records and all 112 OOD records are byte-identical**. train and val are unchanged except the 8 new train seeds. If the final run must use the exact old test set, pull before you retrain and tell me; otherwise the 26 new T5 cases are now part of test.

## Train seeds (8 seeds / 16 records) — no relock
All use the `account_type` mechanism, because that is the only two-check disagreement whose policies are already **train-only** (so no policy crosses splits).

| Seeds | Domain | Count | Policy | Action |
|---|---|---|---|---|
| IND-FIN-T5-005 | FIN | 1 | P_FIN_07 | transfer_money |
| IND-PRIV-T5-005, 006 | PRIV | 2 | P_PRIV_11 | share_file |
| IND-ACC-T5-008, 009, 010 | ACC | 3 | P_ACC_05 | grant_permission |
| IND-ACC-T5-011 | ACC | 1 | P_ACC_20 | grant_permission |
| IND-ACC-T5-012 | ACC | 1 | P_ACC_30 | grant_permission (reversed: employee is the bad value) |

Effect: train 252 → 268 records; **T5-with-two-checks train records 10 → 26** (the scarce case you flagged).

## Test seeds (13 seeds / 26 records) — relocked
All use **test-only** policies, so they slot straight into test.

| Seeds | Domain | Count | Policy | Mechanism (two checks) |
|---|---|---|---|---|
| IND-REPO-T5-004, 005, 006 | REPO | 3 | P_REPO_15 | check_repository_status vs check_repository_compliance (modifiable) |
| IND-FIN-T5-006, 007 | FIN | 2 | P_FIN_18 | check_recipient_type vs check_transfer_compliance (registered_vendor) |
| IND-PRIV-T5-007, 008 | PRIV | 2 | P_PRIV_34 | check_recipient_type vs check_user_authorization (recipient_class) |
| IND-ACC-T5-013 | ACC | 1 | P_ACC_14 | check_user_authorization vs check_user_clearance (role_eligible / seniority) |
| IND-FILE-T5-007, 008, 009 | FILE | 3 | P_FILE_12 | check_file_classification vs check_file_sharing (exposure) |
| IND-FILE-T5-010, 011 | FILE | 2 | P_FILE_26 | check_file_classification vs check_retention_status (disposable) |

Effect: test 124 → 150 records; **T5-with-two-checks test records 16 → 42**.

## On CAL
You asked to cover the thin domains (FIN, PRIV, REPO, CAL). **CAL cannot host a facts_disagree case**: no CAL policy's deciding fact is answered by two different checks, and CAL has no composite "two-facts-must-agree" policy (unlike FILE's P_FILE_12/P_FILE_26). Building one would need a new CAL policy or tool, which we agreed not to invent. So I reallocated CAL's 3 to FILE (its two composite mechanisms give the most variety). If you want CAL covered, we need a new composite CAL policy first.

## Checks run
- `make records`: 570 records, 233 seeds, **0 problems**, 0 flags on the new records.
- Audit of all 42 new records (via `src/data_gen/auto_checks.check_record`): **0 problems, 0 flags, 0 invented tools, 0 policy/action mismatches**, all end on an agent turn, trajectory lengths 4-8 turns, every proposed-action value sourced in the conversation.
- `tests/test_locked_test_set.py`, `test_records.py`, `test_data_gen.py`: 27 passed.
- Changelog row in `docs/decisions.md` (2026-11-06, R11.2/R11.3).
