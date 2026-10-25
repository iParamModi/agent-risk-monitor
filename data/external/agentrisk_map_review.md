# AgentRisk label map: review sheet

Fill in by hand (team), like the ATBench map. Use `data/external/risk_type_categories.txt` for our types.
Write the decision in the Meet and Prateek columns; agreed value in Final. Then the map is applied by code.
Counts are over UNSAFE items (severity above the threshold in Q1), train + dev.

## Q1. Severity threshold (risk_label)

| Severity | Items | SAFE or UNSAFE? (Meet) | (Prateek) | Final |
|---|---|---|---|---|
| 1 Minimal | 331 | | | |
| 2 Low | 41 | | | |
| 3 Moderate | 159 | | | |
| 4 High | 171 | | | |
| 5 Critical | 9 | | | |

Current code: 1 → SAFE, 2–5 → UNSAFE (`SAFE_MAX_SEVERITY` in `src/external/agentrisk.py`).

## Q2. Harm domain → our risk_type

Our types: DATA_LOSS, PRIVACY_LEAKAGE, FINANCIAL_LOSS, ACCESS_CONTROL, SECURITY, OTHER.

| Harm domain | UNSAFE items | Example IDs | risk_type (Meet) | (Prateek) | Final |
|---|---|---|---|---|---|
| Privacy / Confidentiality | 223 | AR-003, AR-005, AR-007 | | | |
| Security / System Integrity | 81 | AR-034, AR-042, AR-045 | | | |
| Financial / Assets | 66 | AR-014, AR-016, AR-021 | | | |
| Physical / Health | 64 | AR-005, AR-017, AR-020 | | | |
| Operational / Service | 55 | AR-017, AR-026, AR-041 | | | |
| Legal / Compliance | 19 | AR-054, AR-158, AR-180 | | | |
| Reputational / Social / Psychological | 8 | AR-168, AR-341, AR-438 | | | |
| Environmental | 3 | AR-054, AR-698, AR-155 | | | |
| Information Quality | 3 | AR-261, AR-457, AR-409 | | | |
| Discrimination / Fairness | 2 | AR-297, AR-275 | | | |

## Q3. Items with two harm domains (144 UNSAFE items)

Our records have one risk_type. Rule for picking one (e.g. a fixed priority order, or label these one by one):

- Meet: 
- Prateek: 
- Final: 

## Q4. Risk driver → our risk_cause (optional)

Our causes: ENVIRONMENT_STATE, USER_REQUEST, AGENT_ERROR, POLICY_CONFLICT, UNTRUSTED_CONTENT.

| Risk driver | UNSAFE items | Example IDs | risk_cause (Meet) | (Prateek) | Final |
|---|---|---|---|---|---|
| Untrusted / Conflicting Instructions | 244 | AR-005, AR-007, AR-010 | | | |
| Authorization / Consent Failure | 159 | AR-005, AR-007, AR-021 | | | |
| Scope / Safeguard Failure | 135 | AR-003, AR-010, AR-014 | | | |
| Insufficient Grounding / Uncertainty | 76 | AR-016, AR-017, AR-020 | | | |
| Execution / Action Hazard | 32 | AR-054, AR-061, AR-100 | | | |
| Risky Requested Outcome | 17 | AR-168, AR-199, AR-221 | | | |

## Q5. Flagged items: keep or exclude from training?

| Flag | Meaning | Items | Keep / exclude (Meet) | (Prateek) | Final |
|---|---|---|---|---|---|
| `reply_to_user` | proposed action talks to the user (refusal, question) instead of acting | 262 | | | |
| `physical_world` | Physical / Health harm in a device or physical setting (cf. the R-Judge exclusion, R12.3) | 61 | | | |
| `rjudge_prompt_overlap` | first user request is word-for-word the same as in an R-Judge record | 69 | | | |
| `rjudge_near_duplicate` | shares > 30% of its 8-word shingles with one R-Judge record | 2 | | | |

## Sign-off

- [ ] Meet
- [ ] Prateek
