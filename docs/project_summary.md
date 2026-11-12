# Agent-Risk monitor: what we built and what we found

Team Catalyst (Param: data, Prateek: environment and deployment, Meet: model and metrics, Moiesha: experiments). Written by Meet, 11 Nov 2026, for anyone who has to understand the whole project quickly (teammates, the final report, a reviewer). Final submission: 14 Nov 2026. Detailed numbers: `docs/reports/final_report_results.md`; every metric: `docs/reports/final_results.md`.

## 1. The problem

An LLM agent works inside a company (files, email, permissions, payments, repositories, calendar). Before each write action, a **monitor** model reads the conversation and the proposed action, plus a few company policies, and answers:

- **ALLOW**, **ASK_CONFIRMATION** (ask the user first), **BLOCK**, or **ESCALATE** (facts or policies conflict: a human must look);
- plus a risk label (SAFE/UNSAFE), a risk type (PRIVACY_LEAKAGE, SECURITY, ACCESS_CONTROL, FINANCIAL_LOSS, DATA_LOSS, OTHER) and evidence (facts and policy numbers).

The fact that decides the case is often **not in the conversation** (is this file shared outside the company? is this user the last admin? did this fact change after the agent read it?). So the monitor may call read-only **check tools** before deciding.

**Research question.** Can a small model learn to check *selectively* (only the facts it needs) and stay about as safe as checking everything, at a fraction of the cost?

## 2. The four checking settings (same records, same model)

| Setting | Checks before deciding | Role |
|---|---|---|
| never | none: decide from the conversation | lower bound, no cost |
| always | every check of a fixed table for the action (about 4.5-5 per record) | safe but expensive reference |
| **selective** | the checks the model asks for itself (NEED_INFORMATION), at most 4 calls, one retry after a tool error | **our method** |
| oracle | exactly the gold label's required checks | upper bound for checking |

Two policy conditions: **correct policies** (the gold policies + 2 look-alike policies, shuffled and numbered; retrieval assumed perfect: the main test of checking) and **retrieved policies** (the top 3 from our retriever: the full system).

## 3. Data

### 3.1 Our generated records (the main evaluation)

Hand-written **seeds** (one scenario each), turned into records by code + hand (`docs/seed_to_record.md`), with gold labels computed by code from the policy rules (`src/policies/gold_engine.py`, `trust_rule.py`), never by an LLM.

| | Seeds | Records |
|---|---|---|
| In-domain (6 domains: ACC 112, FILE 108, PRIV 94, FIN 74, REPO 66, CAL 28 records) | 200 | 482 |
| OOD (new CUST domain + reworded other domains, new tools) | 45 | 112 |

Case types (each seed gives 2 or 4 records with the same visible text but different hidden facts, or a reworded version):

| Type | What it tests | Check needed | In-domain records |
|---|---|---|---|
| T1 | deciding fact hidden (A/B pair: same text, opposite answer) | 1 | 158 |
| T2 | a tool result is in the conversation: a fresh (trust it), b about another resource, c the fact changed since, d only the agent states it | a: 0; b, c, d: 1 | 164 |
| T3 | clearly safe | 0 | 30 |
| T4 | clearly unsafe, visible in the conversation | 0 | 38 |
| T5 | policy conflict (no check) or two facts that disagree (2 checks) → ESCALATE | 0 or 2 | 92 |

**Splits** by seed, and seeds that share a gold policy stay in one split (no policy text decides both a train and a test case): train 292 records / 122 seeds, val 40 / 16, **test 150 / 62 (locked)**, **OOD 112 / 45 (locked, test only)**. Locked files are hashed (`data/LOCKED_TEST.sha256`). Evaluation uses phase-1 tools only: test 146 records (4 `create_event` records left out), train 290 for training (2 records with no check tool for their fact left out).

History: test was 124 records on 30 Oct; Param added 13 two-check T5 seeds (26 records) on 6 Nov, plus 8 such seeds to train (T5 two-check train records 10 → 26), distractor turns in 26 train records (to break an "error message → unsafe" shortcut), and 12 seeds / 24 train records with 10 new write tools (phase 2).

**Policy store:** 154 in-domain policies (170 in the OOD store), each with machine-readable logic (`data/policies/policy_logic.yaml`) and conflict pairs (`conflicts.yaml`). **Check tools:** 28 typed read-only tools (`configs/check_tools.yaml`, 2 OOD-only), answered by a **check gateway** (`src/gateway/`) from each record's hidden company state; it logs every call, enforces the call limit and can add noise (flip facts) for ablations.

### 3.2 Collected datasets (risk detection only)

| Dataset | Records | Train / val / test | Licence note |
|---|---|---|---|
| R-Judge | 531 | 369 / 47 / 115 | |
| ATBench | 999 | 699 / 100 / 200 | |
| AgentRisk (SemEval) | 617 | 394 / 98 / 125 | no licence: never committed or uploaded |

Their labels were mapped to our 6 risk types; ambiguous ones were labelled **by hand, without any LLM** (team rule): 237 R-Judge reviews, a blind 30-row double check (κ 0.57, below the 0.6 target, so a guided blind re-check followed), 25 ATBench misinformation records, 142 AgentRisk types, 281 AgentRisk causes, 58 untyped train records. Training list (`phase_a_train.txt`): PRIVACY_LEAKAGE downsampled, each source 50/50 SAFE/UNSAFE: 1,034 examples (41 over 4,096 tokens dropped in training).

## 4. Method

- **Monitor model:** Qwen3-8B (pinned revision), float16 for evaluation, greedy decoding, Kaggle T4 x2.
- **Prompt** (`prompts/monitor_v1.txt`): conversation, proposed action, 3 numbered policies (ids hidden), the check tools with their arguments and return fields; answer in strict JSON. The collected datasets use a risk-only prompt (`monitor_risk_v1.txt`).
- **Retriever** (`src/policies/retriever.py`): hybrid BM25 + `bge-base-en-v1.5`, weight 0.6, query = action + all user and agent turns, top 3. Tuned on train + val: **recall@3 0.55**, @5 0.62.
- **Fine-tuning** (`src/training/`): QLoRA (r 16, alpha 32, lr 2e-4, 2 epochs, 4-bit NF4, max 4,096 tokens), targets built by code from gold, loss on the answer only.
  - **Phase A:** collected data only (1,034 examples): risk label + type.
  - **Phase B (final, 10-11 Nov):** our 290 train records → 988 examples (first pass: DECISION or NEED_INFORMATION with the gold checks; second pass: the gateway's results → DECISION; our examples repeated 2x) + the same 1,034 collected examples = 2,022 (1,981 kept). Train loss 0.031, eval loss 0.024 → 0.025 over the 2 epochs, about 6.5 h. Private Kaggle dataset `meet6868/agent-risk-adapter-final`.
- **Rule baselines** (`src/baselines/`): hand-written if-then rules over shown policy text and facts: *rules only* (never checks) and *rules + environment* (always checks).
- **Metrics** (`src/eval/`, `docs/evaluation_metrics.md`): decision accuracy; **unsafe action rate** (risky records let through: decision weaker than gold); wrong-block rate; checks per record and saving vs always; check precision/recall; right missing fact; decision macro-F1; risk-label F1; risk-type macro-F1; valid JSON. 95% intervals by bootstrap over seeds (2,000 resamples), McNemar and Wilcoxon tests.
- **Hypothesis (R10.4, fixed before any result):** selective is not less safe than always: the upper end of the 95% interval of Δ unsafe (selective − always) is at most **+5 points**.

## 5. Results (final adapter)

### 5.1 Our records, decision accuracy (%)

| Method / setting | Test (146) correct pol. | Test retrieved | OOD (112) correct pol. | OOD retrieved | Val (40) correct pol. | Val retrieved |
|---|---|---|---|---|---|---|
| Rules only | 43.8 | 43.8 | 54.5 | 54.5 | 57.5 | 57.5 |
| Rules + environment | 52.1 | 52.7 | 54.5 | 47.3 | 65.0 | 50.0 |
| Base, selective | 43.8 | 39.0 | 58.0 | 46.4 | 70.0 | 57.5 |
| Phase B, never | 61.0 | 58.2 | 67.9 | 60.7 | 75.0 | 67.5 |
| Phase B, always | 75.3 | 65.8 | 66.1 | 59.8 | 82.5 | 70.0 |
| **Phase B, selective** | **69.2** | **61.6** | **78.6** | **67.0** | **82.5** | **67.5** |
| Phase B, oracle | 86.3 | 76.0 | 87.5 | 75.9 | 97.5 | 90.0 |

Checks per record: selective 0.71-0.76, always 4.50-5.00 (**about 85% fewer**, p < 0.001).

### 5.2 Hypothesis: Δ unsafe action rate, selective − always (Phase B)

| | Correct policies (main) | Retrieved policies |
|---|---|---|
| Test | **+29.3 [16.7, 42.2]: fails, selective clearly less safe** | +18.3 [8.2, 28.9]: fails |
| OOD | −3.9 [−17.0, 8.9]: inconclusive | 0.0 [−13.2, 13.2]: inconclusive |
| Val | 0.0 [−21.1, 21.1]: inconclusive | +10.5 [−18.2, 41.2]: inconclusive |

### 5.3 Does it learn to ask, and ask the right thing? (selective, correct policies)

| | Base | Phase B |
|---|---|---|
| Asks when a check is needed (test / OOD) | 53.1 / 33.8 | 87.7 / 91.5 |
| Right check among asked (test / OOD) | 67.4 / 75.0 | 81.7 / 80.0 |
| Decision right when every needed check was made (test / OOD) | 56.0 / 83.3 | 94.2 / 94.2 |
| T2c (fact changed): asks | 0% | 100% |
| T5 two facts disagree: both checks made (test, 34) | 5.9% | 11.8% |

Same records for all three models (test: the original 120); the 30 Oct adapter asked more often (97.5 / 97.2) but was otherwise similar.

### 5.4 Errors (Phase B, selective)

- Retrieved policies: **a retrieval miss is the first cause of 48 of 56 test errors, 26 of 37 OOD errors, 10 of 13 val errors.** Given the correct policies, only 12 of the 48 test ones become right (OOD 17 of 26, val 6 of 10): the retrieval ceiling is +7.6 points on test, +11.6 on OOD, +15 on val.
- Correct policies: 45 test errors, **22 of them two-check T5 records where only one check was made**; 10 wrong fact checked, 8 right fact but wrong decision, 5 no check.
- OOD records with new tools: selective 59.5 (retrieved) vs 71.4 on records with only new wording.

### 5.5 Collected datasets (test, 428 records; risk only)

| | Accuracy | Risk-label F1 | Risk-type macro-F1 |
|---|---|---|---|
| Base | 54.9 | 32.8 | 26.1 |
| Phase A | 92.8 | 91.9 | 55.0 |
| Phase B, 30 Oct | 91.4 | 90.2 | 50.0 |
| Phase B, final | 90.4 | 89.0 | 52.7 |
| Word model, no LLM | 88.6 | | |

Shortcut check: most of the gain can be reached from wording alone; R-Judge has 43 near-copies of training records in its 115 test records; AgentRisk's "reply to the user = SAFE" rule gets 85.6; ATBench's error-message shortcut cannot be tested on val/test.

### 5.6 System v2 (12 Nov): the final system

Inference only, same adapter: retrieval ranks only the policies tagged with the proposed action's tool and shows 8; selective adds the second-source check and two prompt hints. Phase B, v1 -> v2 (`final_results_v2.md`, `report_extras.md`):

| | Selective, retrieved | Selective, correct | Unsafe, selective retrieved | Unsafe, always retrieved | Oracle, retrieved |
|---|---|---|---|---|---|
| Test | 61.6 -> 63.0 | 69.2 -> 69.9 | 52.4 -> 39.0 | 34.1 -> 24.4 | 76.0 -> 80.8 |
| OOD | 67.0 -> 66.1 | 78.6 -> 80.4 | 37.3 -> 35.3 | 37.3 -> 29.4 | 75.9 -> 82.1 |
| Val | 67.5 -> 77.5 | 82.5 -> 85.0 | 52.6 -> 42.1 | 42.1 -> 36.8 | 90.0 -> 90.0 |

Safer, about the same accuracy; the hypothesis still fails on test (Δ unsafe, retrieved: +14.6 [0.0, 29.7]). The second-source rule fired on 1 test record: it covers facts two tools report (the train two-check mechanism), while 32 of 34 two-check test records combine two different facts. The v3 candidates (only the action's check tools; one more ask) were not run: Kaggle weekly GPU quota used up.

### 5.7 Cost hypotheses (exploratory, stated after the results; `cost_hypotheses.md`)

Phase B v2, selective vs always: **check calls** 0.15-0.17 of always (holds everywhere); **model tokens** about 2.4x always (does not hold: the prompt lists every check tool and most records take a second pass), so selective is cheaper only where a check call costs more than about 350-400 tokens; **accuracy within 5 points** not shown on test (intervals too wide; −5.5 with correct policies), selective ahead on OOD with correct policies (+14.3 [3.4, 25.0]); **beats rules that run every check** by 16-26 points with one sixth of the checks.

## 6. What we conclude

1. Fine-tuning teaches an 8B model to monitor agents with checks: Phase B beats base and both rule baselines everywhere, and the skill carries over to a new domain (OOD).
2. Selective checking costs about 15% of always-checking, and the model learns **when** to ask (especially for stale or untrusted tool results) and mostly **what** to ask.
3. It is **not** as safe as always-checking on in-domain test, mainly because it makes one check when two are needed (facts that disagree), and because a retrieval miss leads to the wrong check.
4. Retrieval misses are the most common first cause of errors in the full system, but the ceiling is smaller (+7.6 points on test). Tag-filtered retrieval (v2) cuts the unsafe rate (test, selective 52.4 -> 39.0) without changing accuracy much.
5. Two-check cases that combine two different facts need new training data; no inference rule fixes them.

## 7. Not done / open

v3 val check (no GPU quota), retrain with two-check data of new mechanisms (S7, S8), ablations (no policies, check noise, top-k), Qwen3-235B comparison, 50 human evidence checks, κ study on our records, demo / service / live runs with 2 agent LLMs (see `PROGRESS.md`).

## 8. Constraints any change must respect

- Test (`data/records/test.jsonl`) and OOD (`ood_test.jsonl`) are locked: no training, tuning or choosing on them; only val (40 records) may guide changes.
- No LLM may make or suggest risk-type labels (team rule, `CLAUDE.md` §6).
- AgentRisk data is never committed or uploaded; adapters stay private.
- Compute: Kaggle T4 x2, at most 2 GPU jobs at once, 12 h per job; one Phase B retrain takes about 6.5 h, a full evaluation of one model on val + test + OOD about 5 h.
