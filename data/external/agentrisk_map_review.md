# AgentRisk label map: review sheet

Fill in by hand (team), like the ATBench map. Use `data/external/risk_type_categories.txt` for our types.
Write the decision in the Meet and Prateek columns; agreed value in Final. Then the map is applied by code.
Counts are over UNSAFE items (severity above the threshold in Q1), train + dev.

## Q1. Severity threshold (risk_label)

| Severity | Items | SAFE or UNSAFE? (Meet) | (Prateek) | Final |
|---|---|---|---|---|
| 1 Minimal | 331 | SAFE | | |
| 2 Low | 41 | left out (unclear middle) | | |
| 3 Moderate | 159 | UNSAFE | | |
| 4 High | 171 | UNSAFE | | |
| 5 Critical | 9 | UNSAFE | | |

Current code: 1 → SAFE, 2 → left out, 3–5 → UNSAFE (`SEVERITY_LABEL` in `src/external/agentrisk.py`). Counts below are over the records kept.

## Q2. Harm domain → our risk_type

Our types: DATA_LOSS, PRIVACY_LEAKAGE, FINANCIAL_LOSS, ACCESS_CONTROL, SECURITY, OTHER.

| Harm domain | UNSAFE items | Example IDs | risk_type (Meet) | (Prateek) | Final |
|---|---|---|---|---|---|
| Privacy / Confidentiality | 217 | AR-005, AR-007, AR-010 | PRIVACY_LEAKAGE |  |  |
| Security / System Integrity | 77 | AR-034, AR-042, AR-045 | SECURITY |  |  |
| Physical / Health | 54 | AR-005, AR-017, AR-020 | OTHER |  |  |
| Financial / Assets | 54 | AR-014, AR-016, AR-026 | FINANCIAL_LOSS |  |  |
| Operational / Service | 41 | AR-017, AR-026, AR-061 | by situation, labelled per record by hand (`agentrisk_recheck.csv`) |  |  |
| Legal / Compliance | 17 | AR-158, AR-180, AR-221 | OTHER |  |  |
| Reputational / Social / Psychological | 8 | AR-168, AR-341, AR-438 | OTHER |  |  |
| Information Quality | 3 | AR-261, AR-457, AR-409 | by situation, labelled per record by hand (`agentrisk_recheck.csv`) |  |  |
| Discrimination / Fairness | 2 | AR-297, AR-275 | OTHER |  |  |
| Environmental | 2 | AR-698, AR-155 | OTHER |  |  |

Situation rule (Meet, 2026-10-26) for Operational / Service and Information Quality, from the guide:
system made unstable, forced shutdown, processes killed → SECURITY; files moved or hidden without consent → SECURITY; deleting apps or files, clearing data, overwriting records → DATA_LOSS; physical or emergency harm (dispatch, health) → OTHER.

## Q3. Items with two harm domains (136 UNSAFE items)

Meet, 2026-10-26:

- 34 include Operational / Service or Information Quality → per record (reason "mixed domain").
- 4 where both domains map to OTHER (Legal + Discrimination 2, Legal + Reputational 1, Environmental + Legal 1) → OTHER.
- 98 where the two domains map to different types (incl. a named type + an OTHER domain) → **per record**, by hand, choosing only between the 2 types (reason "two domains" in `agentrisk_recheck.csv`; label the harm the proposed action itself causes, guide Rule 2).
- The 142 per-record items (98 + 44 mixed) were all labelled by Meet (2026-10-26); how-to: `agentrisk_recheck_HOWTO.md`.
- Prateek: 
- Final: 

## Q4. Risk driver → our risk_cause (optional)

Our causes: ENVIRONMENT_STATE, USER_REQUEST, AGENT_ERROR, POLICY_CONFLICT, UNTRUSTED_CONTENT.

| Risk driver | UNSAFE items | Example IDs | risk_cause (Meet) | (Prateek) | Final |
|---|---|---|---|---|---|
| Untrusted / Conflicting Instructions | 240 | AR-005, AR-007, AR-010 | UNTRUSTED_CONTENT |  |  |
| Authorization / Consent Failure | 153 | AR-005, AR-007, AR-025 | ENVIRONMENT_STATE or AGENT_ERROR |  |  |
| Scope / Safeguard Failure | 127 | AR-010, AR-014, AR-024 | AGENT_ERROR |  |  |
| Insufficient Grounding / Uncertainty | 53 | AR-016, AR-017, AR-020 | ENVIRONMENT_STATE |  |  |
| Execution / Action Hazard | 25 | AR-061, AR-135, AR-154 | AGENT_ERROR |  |  |
| Risky Requested Outcome | 17 | AR-168, AR-199, AR-221 | USER_REQUEST |  |  |

Meet, 2026-10-26: an item's options = the causes of all its drivers. One option (58 UNSAFE items) → decided by this map; more (281) → per record by hand by **Meet** (all 281; taken back from Prateek, 2026-10-26) in `agentrisk_cause_recheck.csv` (`python scripts/show_agentrisk_recheck.py --cause Meet`). Needs a schema change before applying: external records must have risk_cause = null today (R3.4).

## Q5. Flagged items: keep or exclude from training?

| Flag | Meaning | Items | Keep / exclude (Meet) | (Prateek) | Final |
|---|---|---|---|---|---|
| `reply_to_user` | proposed action talks to the user (refusal, question) instead of acting | 250 | keep; report test results with and without them (all SAFE: shortcut) | | |
| `physical_world` | Physical / Health harm in a device or physical setting (cf. the R-Judge exclusion, R12.3) | 51 | exclude (as R-Judge, R12.3) | | |
| `rjudge_prompt_overlap` | first user request is word-for-word the same as in an R-Judge record | 64 | keep; report test results with and without them (same request, different conversation; 19 cross the train/test line) | | |
| `rjudge_near_duplicate` | shares > 30% of its 8-word shingles with one R-Judge record | 2 | exclude | | |

Meet, 2026-10-26: excluded items are dropped after the split (split unchanged), listed in `agentrisk_report.json` `excluded_flags`.

**Applied (Meet, 2026-10-26)** by `python -m src.external.agentrisk` (`map_labels`): 617 records kept (train 394 / val 98 / test 125).
UNSAFE 288: PRIVACY_LEAKAGE 195, SECURITY 39, FINANCIAL_LOSS 28, OTHER 16, DATA_LOSS 10 (no ACCESS_CONTROL);
causes UNTRUSTED_CONTENT 199, AGENT_ERROR 44, ENVIRONMENT_STATE 30, USER_REQUEST 15. Hand labels used: 101 types, 244 causes
(the rest belong to excluded items). If Prateek changes an answer, change the map in `src/external/agentrisk.py` and rerun.

## Sign-off

- [ ] Meet
- [ ] Prateek
