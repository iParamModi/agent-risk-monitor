# Retrieval on in-domain seeds (first estimate)

Policies: 138 (temporary store). Seeds: 162. Query = proposed action + story_hint. score = w · embeddings + (1 − w) · BM25.

| w | recall@1 | recall@3 | recall@5 | all gold in top 3 | T5 conflict recall@3 |
|---|---|---|---|---|---|
| 0.0 | 29.0 | 58.6 | 64.8 | 57.4 | 76.9 |
| 0.1 | 30.2 | 57.4 | 66.0 | 55.6 | 76.9 |
| 0.2 | 31.5 | 58.0 | 66.0 | 56.2 | 76.9 |
| 0.3 | 32.7 | 60.5 | 66.0 | 58.6 | 76.9 |
| 0.4 | 32.7 | 61.1 | 66.0 | 59.3 | 76.9 |
| 0.5 | 34.6 | 61.7 | 67.9 | 59.3 | 69.2 |
| 0.6 | 35.8 | 62.3 | 71.0 | 60.5 | 76.9 |
| 0.7 ← | 38.3 | 64.8 | 72.2 | 62.3 | 69.2 |
| 0.8 | 40.1 | 63.0 | 70.4 | 60.5 | 69.2 |
| 0.9 | 41.4 | 60.5 | 69.8 | 58.0 | 69.2 |
| 1.0 | 37.0 | 58.0 | 66.7 | 54.9 | 61.5 |

Best w = 0.7 (highest recall@3; ties go to the w closest to 0.5). Not final: w is tuned on val seeds after Step 5 + the seed split.

## recall@3 by domain (w = 0.7)

| domain | seeds | recall@3 |
|---|---|---|
| ACC | 36 | 86.1 |
| CAL | 10 | 70.0 |
| FILE | 38 | 65.8 |
| FIN | 25 | 40.0 |
| PRIV | 30 | 63.3 |
| REPO | 23 | 56.5 |

## recall@3 by case_type (w = 0.7)

| case_type | seeds | recall@3 |
|---|---|---|
| T1 | 62 | 51.6 |
| T2 | 41 | 53.7 |
| T3 | 15 | 93.3 |
| T4 | 19 | 89.5 |
| T5 | 25 | 80.0 |

## Misses at w = 0.7 (57)

| seed | gold | top 3 |
|---|---|---|
| IND-ACC-T1-003 | P_ACC_05 | P_ACC_03, P_PRIV_18, P_ACC_08 |
| IND-ACC-T1-006 | P_ACC_05 | P_ACC_03, P_ACC_08, P_ACC_16 |
| IND-ACC-T2-001 | P_ACC_02 | P_ACC_03, P_ACC_16, P_ACC_31 |
| IND-ACC-T2-003 | P_ACC_22 | P_ACC_03, P_ACC_18, P_ACC_08 |
| IND-ACC-T5-003 | P_ACC_05 | P_ACC_08, P_ACC_03, P_ACC_21 |
| IND-CAL-T1-001 | P_CAL_01 | P_CAL_03, P_CAL_10, P_CAL_11 |
| IND-CAL-T2-001 | P_CAL_02 | P_PRIV_22, P_CAL_10, P_CAL_09 |
| IND-CAL-T2-002 | P_CAL_07 | P_CAL_01, P_CAL_10, P_CAL_09 |
| IND-FILE-T1-002 | P_FILE_04 | P_FILE_02, P_FILE_05, P_FILE_37 |
| IND-FILE-T1-003 | P_FILE_01 | P_FILE_05, P_ACC_19, P_FILE_03 |
| IND-FILE-T1-005 | P_FILE_09 | P_FILE_19, P_FILE_22, P_FILE_02 |
| IND-FILE-T1-009 | P_FILE_13 | P_PRIV_35, P_PRIV_23, P_ACC_08 |
| IND-FILE-T1-011 | P_FILE_18 | P_REPO_10, P_FILE_05, P_FILE_02 |
| IND-FILE-T1-013 | P_FILE_20 | P_FILE_25, P_FILE_37, P_FILE_26 |
| IND-FILE-T2-001 | P_FILE_04 | P_FILE_02, P_FILE_37, P_FILE_26 |
| IND-FILE-T2-002 | P_FILE_13 | P_PRIV_35, P_PRIV_23, P_FILE_32 |
| IND-FILE-T2-003 | P_FILE_27 | P_PRIV_03, P_ACC_09, P_FILE_33 |
| IND-FILE-T2-004 | P_FILE_36 | P_PRIV_24, P_FILE_22, P_FILE_02 |
| IND-FILE-T2-005 | P_FILE_31 | P_FILE_37, P_FILE_26, P_PRIV_14 |
| IND-FILE-T2-007 | P_FILE_33 | P_PRIV_03, P_PRIV_19, P_FILE_09 |
| IND-FILE-T2-009 | P_FILE_35 | P_FILE_19, P_FILE_22, P_FILE_02 |
| IND-FIN-T1-001 | P_FIN_01 | P_FIN_18, P_FIN_04, P_FIN_07 |
| IND-FIN-T1-002 | P_FIN_18 | P_FIN_04, P_FIN_03, P_FIN_17 |
| IND-FIN-T1-003 | P_FIN_08 | P_FIN_04, P_FIN_03, P_FIN_14 |
| IND-FIN-T1-004 | P_FIN_19 | P_FIN_18, P_FIN_04, P_FIN_07 |
| IND-FIN-T1-006 | P_FIN_09 | P_FIN_04, P_FIN_03, P_FIN_14 |
| IND-FIN-T1-007 | P_FIN_20 | P_FIN_04, P_FIN_03, P_FIN_14 |
| IND-FIN-T1-008 | P_FIN_10 | P_FIN_04, P_FIN_03, P_FIN_21 |
| IND-FIN-T1-009 | P_FIN_21 | P_FIN_04, P_FIN_03, P_FIN_14 |
| IND-FIN-T2-002 | P_FIN_14 | P_FIN_04, P_FIN_03, P_FIN_20 |
| IND-FIN-T2-004 | P_FIN_14 | P_FIN_04, P_FIN_03, P_FIN_10 |
| IND-FIN-T2-006 | P_FIN_14 | P_FIN_04, P_FIN_03, P_FIN_20 |
| IND-FIN-T3-002 | P_FIN_15 | P_FIN_04, P_FIN_11, P_FIN_03 |
| IND-FIN-T4-001 | P_FIN_02 | P_FIN_04, P_FIN_03, P_FIN_11 |
| IND-FIN-T5-001 | P_FIN_07 | P_FIN_04, P_FIN_03, P_FIN_18 |
| IND-FIN-T5-003 | P_FIN_07 | P_FIN_04, P_FIN_03, P_FIN_14 |
| IND-PRIV-T1-001 | P_PRIV_01 | P_PRIV_27, P_PRIV_05, P_PRIV_16 |
| IND-PRIV-T1-005 | P_PRIV_11 | P_PRIV_03, P_FILE_09, P_ACC_03 |
| IND-PRIV-T1-006 | P_PRIV_28 | P_ACC_11, P_PRIV_16, P_ACC_10 |
| IND-PRIV-T1-007 | P_PRIV_14 | P_FILE_10, P_PRIV_08, P_FILE_33 |
| IND-PRIV-T1-008 | P_PRIV_29 | P_PRIV_05, P_PRIV_16, P_CAL_09 |
| IND-PRIV-T1-010 | P_PRIV_30 | P_PRIV_03, P_ACC_10, P_ACC_11 |
| IND-PRIV-T1-011 | P_PRIV_31 | P_FILE_10, P_PRIV_08, P_PRIV_03 |
| IND-PRIV-T2-002 | P_PRIV_09 | P_CAL_08, P_PRIV_05, P_CAL_06 |
| IND-PRIV-T2-003 | P_PRIV_21 | P_PRIV_03, P_ACC_09, P_FILE_09 |
| IND-PRIV-T4-003 | P_PRIV_17 | P_PRIV_05, P_CAL_04, P_PRIV_06 |
| IND-PRIV-T5-004 | P_PRIV_18 | P_PRIV_03, P_FILE_12, P_ACC_22 |
| IND-REPO-T1-001 | P_REPO_01 | P_REPO_14, P_REPO_17, P_REPO_04 |
| IND-REPO-T1-004 | P_REPO_07 | P_REPO_14, P_REPO_04, P_REPO_17 |
| IND-REPO-T1-005 | P_REPO_17 | P_REPO_14, P_REPO_04, P_REPO_12 |
| IND-REPO-T1-006 | P_REPO_08 | P_REPO_10, P_REPO_14, P_REPO_16 |
| IND-REPO-T1-007 | P_REPO_18 | P_REPO_14, P_REPO_04, P_REPO_17 |
| IND-REPO-T1-008 | P_REPO_09 | P_REPO_14, P_REPO_04, P_REPO_17 |
| IND-REPO-T2-001 | P_REPO_02 | P_REPO_03, P_REPO_14, P_REPO_04 |
| IND-REPO-T2-003 | P_REPO_02 | P_REPO_14, P_REPO_03, P_FILE_37 |
| IND-REPO-T2-005 | P_REPO_02 | P_REPO_14, P_REPO_04, P_REPO_18 |
| IND-REPO-T5-002 | P_REPO_15 | P_REPO_14, P_REPO_18, P_REPO_04 |
