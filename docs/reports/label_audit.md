# Label audit by code

Checks that code can make on the gold labels of our records (no LLM, no human judgement). It does not replace the human agreement study (PLAN Step 10, decisions.md R4.5, not done): it finds contradictions, it never says which label is right. Built by `scripts/label_audit.py`.

594 decide_action records (train, val, test, OOD).

| # | Check | Result |
|---|---|---|
| 1 | Merge checks (schema, fields, coverage, T1 pair identity) | pass (0 problems); 29 wording flags for a human; 0 T1 pairs failed |
| 2 | Records rebuilt from `data/generated` equal the committed ones | pass (0 differ) |
| 3 | Test and OOD match the lock | pass (ood_test.jsonl OK, test.jsonl OK) |
| 4 | Near-duplicates across records (dedup threshold) | pass (0 pairs) |
| 5 | Records of one seed with different decisions differ in what a monitor sees | **2 pairs look the same** |
| 6 | T1: same policies, action, fact and value give one decision | pass (168 groups, 0 with two decisions) |
| 7 | Every gold check runs without an error | pass (0 errors) |
| 8 | Seed gold equals the decision of the policy rules | **1 seed(s) differ** |

**Check 5, pairs that look the same:**

- IND-CAL-T1-003-A (train, ALLOW) vs IND-CAL-T1-003-B (ASK_CONFIRMATION), required checks: 0
- IND-CAL-T1-001-A (test, ALLOW) vs IND-CAL-T1-001-B (ASK_CONFIRMATION), required checks: 0

(Records with 0 required checks are phase-2 create_event records, left out of training and evaluation.)

**Check 8, for a person to read** (the coverage script cannot evaluate a condition that is "visible in the action" and assumes the rule fires; it lists the seed, not a verdict):

| seed id | variant | fact value | seed gold | gold from policies | policies involved | note |
|---|---|---|---|---|---|---|
| OOD-CUST-T3-002 | - | - | ALLOW | BLOCK | P_CUST_02 | seed gold or policy logic (own rule gives a different decision) |

Coverage script: `seeds 245, out of scope 16, pass 215, fail 14; rules 170, fail 0; gold mismatches 1; proposed tools 0; literal conditions 0, implicit 0, standalone ESCALATE 0, fact unused 0; sim missing ['check_sole_admin']; tools failing [], warnings 9; hidden-pair problems 0; always setting 2.97 -> 4.80 checks/record`. Its other failing items are seed *notes* that name a check differently from the records (the records' gold checks run and return the deciding fact, checks 5 and 7).
