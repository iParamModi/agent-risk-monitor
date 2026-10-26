# To Prateek: policy_logic generator fixed (your 6 faults)

From Param, 2026-10-27. Re: `docs/messages/2026-10-27_to_Param_policy_logic.md`. Thanks — all six were real. Fixed in the **generator** (`scripts/gen_policy_store.py`, one seed), then regenerated `policy_logic.yaml` + `conflicts.yaml`.

`python scripts/check_tool_coverage.py` section 10 is now all **0**: `literal conditions 0, implicit 0, standalone ESCALATE 0, fact unused 0`.

What I did:
1. **Literal copies** → new `GENERAL` dict with hand-written conditions (`P_FILE_03` `owner != requested_by`, `P_FILE_04`/`P_FILE_13`/`P_PRIV_02` `sharing != internal`, `P_FILE_09`/`P_REPO_04` `owner_team != requester_team`) + a guard that fails if a condition is a bare `user_/org_/acct_` id.
2. **Only-name-the-fact** → `T2_UNSAFE` class per fact (`sharing != internal`, `archived == True`, `status == archived`, `legal_hold == True`) used for T2-only rules.
3. **Standalone ESCALATE** → `P_CUST_14/15/16` added to `T5_STANDALONE`; the six facts_disagree rules (`P_ACC_20`, `P_PRIV_18/34`, `P_FILE_12/26`, `P_REPO_15`) given a `STANDALONE_DECISION` (BLOCK) + condition in `GENERAL`.
4. **P_ACC_30** → `resource in {vendor_portal, vendor-portal} and account_type == employee`. **P_ACC_20** → scoped `resource == source_code and account_type != employee`.
5. **P_FIN_10** → `amount_inr > 100000 and not dual_approval_obtained`.
6. **Two fact names** → renamed `is_production`→`production` in `IND-REPO-T1-009`; `P_CUST_01` and `P_CUST_04` conditions in `GENERAL`; guard that fails on >1 fact name unless in `GENERAL`.

**Schema:** relaxed `record.schema.json` so `required_checks` may be `null` while `check_needed` is true (filled in a later pass once your check tools are final — `seed_to_record.md` D4).

## One thing back to you — the 3 remaining section-5 mismatches are the checker, not the rules
`IND-FILE-T1-001 A`, `IND-FILE-T1-005 A`, `IND-REPO-T1-002 B` still show as gold mismatches, but the conditions are **correct** — `check_tool_coverage.py` just doesn't substitute `requested_by` / `requester_team` (the requester-relative names your fault-1 note says the gold engine must fill). Verified by hand:
- `IND-FILE-T1-001 A`: owner `user_12`, requested_by `user_12` → `owner != requested_by` is False → ALLOW ✓ (matches seed).
- `IND-FILE-T1-005 A`: owner_team `design`, requester `user_31` team `design` → False → ALLOW ✓.
- `IND-REPO-T1-002 B`: owner_team `web`, requester `user_6` team `web` → False → ALLOW ✓.

Could you make the checker resolve `requested_by` (seed field) and `requester_team` (that user's `team` in `start_state.users`)? Then section 5 should be empty too. 343 tests pass.
