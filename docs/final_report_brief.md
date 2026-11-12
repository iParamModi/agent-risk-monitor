# Final report brief: everything the report needs, by section

Meet, 12 Nov 2026. Source material for writing the final report (due 14 Nov 2026). It follows the sections the TA asked for. Every number here comes from a generated report in `docs/reports/`; the file is named next to each block. **If a number here and its source report ever differ, the source report wins.** Nothing in the report may be computed differently or newly invented.

**TA's required sections:** Abstract, Introduction, Literature Review, Dataset created/used, Methodology, Experiment runs, Ablations, Evaluations, Limitations, Conclusions, References. **The report must include the updated GitHub link:** https://github.com/meet6868/Agent-Risk-Monitoring

**Team Catalyst:** Param (data), Prateek (environment and deployment), Meet (model and metrics), Moiesha (experiments).

**Main source files:**

| File | What |
|---|---|
| `docs/reports/final_report_results.md` | one place for all results (sections 1-12); v2 = final system, section 3b |
| `docs/reports/final_results_v2.md` (+ `.json`) | every metric of the final system (v2), val / test / OOD, both policy conditions, rule baselines, base, Phase B |
| `docs/reports/final_results.md` | the same for system v1 (the comparison) |
| `docs/reports/report_extras.md` | cost-safety table, case types, test reweighted, hypothesis power, T2 subtypes, T1 pairs, saving vs oracle |
| `docs/reports/cost_hypotheses.md` | exploratory cost hypotheses C1-C4 |
| `docs/reports/check_results.md` | does the model learn to ask, and ask the right check |
| `docs/reports/error_analysis.md` (val, test, OOD) | first cause of each wrong answer |
| `docs/reports/collected_test_results.md`, `shortcut_check.md` | collected datasets, shortcut check |
| `docs/reports/label_audit.md` | label checks by code |
| `docs/reports/improvement_suggestions.md` | retrieval measurements (section 2), re-ranker trial (section 7), future work |
| `docs/project_summary.md` | plain-language overview |
| `docs/decisions.md` | every design rule (R1-R15) and the Changelog of every change, with dates |
| `report/mid_submission.tex` | the mid report: LaTeX style, tables, Experiment 1 |
| `docs/Catalysts.pdf` | the proposal: related work, references, problem definition, "What we do not claim" |

---

## 1. Abstract (the facts it should carry)

- Problem: a monitor model must approve, question, block or escalate an AI agent's next action inside a company, when the deciding fact is often not in the conversation and must be checked with read-only tools.
- Question: can a small model learn to check **selectively** and stay about as safe as checking everything, with far fewer checks?
- What we built: our own dataset (594 records from 245 hand-written seeds, labels made by code from policy rules), a policy store (154 in-domain / 170 OOD policies), 28 read-only check tools answered by a check gateway over each record's hidden company state, a hybrid policy retriever, and a QLoRA-tuned Qwen3-8B monitor.
- Main results (final system v2, Phase B, test, 146 records): selective makes 0.74-0.80 checks per record vs 4.82 for always (about 85% fewer). Accuracy selective 63.0 (retrieved policies) / 69.9 (correct policies) vs always 62.3 / 75.3. Phase B beats the base model and both rule baselines in every setting.
- Hypothesis (fixed before any result): **fails on test** (Δ unsafe selective − always: +14.6 [0.0, 29.7] retrieved, +26.8 [14.3, 39.5] correct); inconclusive on OOD. Main cause: records that need two checks (selective makes both in about 12%).
- Honest answer: selective is cheaper in check calls, not in model tokens (about 2.4x always).

## 2. Introduction

- **Use the pricing-sheet example** (PLAN Step 25.1; the old example was too close to the AgentRisk website sample). From `docs/PLAN.md` lines 16 and 140-147: the agent proposes writing internal cost numbers into `pricing_v2.xlsx`; whether that is safe depends on whether the file is shared outside the company, which is not in the conversation. The monitor answers NEED_INFORMATION with `check_file_sharing`, sees `sharing = external:org_4`, and blocks under the policy on external sharing. Stale-fact variant (PLAN Step 24.2): the file was moved after the agent last checked it, so an earlier "internal" result can no longer be trusted, and the monitor re-checks.
- Why it matters: guard models label prompts or replies without access to the environment; always checking every fact is expensive (calls to real company systems, latency, access to personal data).
- Contributions (use "to our knowledge" for the novelty claim, PLAN Step 25.3):
  1. a task and dataset where the deciding fact is hidden and must be checked, with A/B pairs that look the same and differ only in the hidden fact, tool results that may or may not be trusted (T2), and conflicts (T5);
  2. a monitor that decides when to check (NEED_INFORMATION) and which check to make, trained with QLoRA;
  3. a comparison of four checking settings (never / always / selective / oracle) with a hypothesis fixed in advance;
  4. an honest negative result on safety and a cost analysis.
- **Keep the "What we do not claim" paragraph** (proposal, `docs/Catalysts.pdf`): "We do not claim to be the first environment-aware monitor, the first to use RAG for agent safety, the first to study hidden state, or the first policy-aware safety system. Our claim is narrower: we study checking only when needed as a way to make policy-based agent safety monitoring work."

## 3. Literature review

From the proposal (`docs/Catalysts.pdf`, Related Work), with the changes PLAN Step 25.2 and 25.6 ask for:

- **Agent safety benchmarks:** R-Judge (Yuan et al., 2024), ATBench, Agent-SafetyBench (Zhang et al., 2024), AgentHarm (Andriushchenko et al., 2025), SafeArena (Tur et al., 2025), OpenAgentSafety (Vijayvargiya et al., 2025), ToolEmu (Ruan et al., 2024). These mostly give fixed, labelled records; the monitor cannot query an environment.
  - **Fix the ATBench citation:** ATBench is Li et al., 2026, arXiv:2604.02022. The proposal cited "Liu et al., 2026", which is the AgentDoG paper.
- **Closest work:** ShieldAgent (Chen et al., 2025): **change the wording to "verifies policy rules using information from the agent's trajectory"**; we study when to check and what it costs compared with always checking. AGrail (Luo et al., 2025): creates safety checks before actions but has no explicit "do I know enough?" step. pi-bench (Das, 2026): agents following policies with hidden state; we test a separate monitor and how selective it is. SABER (Hu et al., 2026): safety from the final state of a workspace, not before the action. TRUST-Bench / Trust No Tool (Yan et al., 2026): hidden triggers with matched safe cases, focused on attacked tool outputs. AgentDoG (Liu et al., 2026): diagnoses risks in agent runs without environment access.
- **Add (PLAN Step 25.2):** PhantomPolicy/Sentinel, Ask the World Before Acting, MIRAGE. **Their full citations are not in the repo**: add them only with verified authors, title, venue/arXiv id and year; otherwise leave a clearly marked TODO for the team.
- **Guard models and related ideas:** Llama Guard (Inan et al., 2023) labels prompts or replies without environment access. Our "do I know enough?" step is close to selective prediction (Geifman and El-Yaniv, 2017) and active feature acquisition (Shim et al., 2018). We use LoRA (Hu et al., 2022), QLoRA (Dettmers et al., 2023), Qwen3 (Qwen Team, 2025), retrieval (Lewis et al., 2020), Cohen's κ (Cohen, 1960).

## 4. Dataset created / used

### 4.1 Our generated records (main evaluation) — `docs/project_summary.md` section 3, `docs/DATASET.md`, `docs/seed_to_record.md`

- Hand-written **seeds** (one scenario each), turned into records by code and by hand; **gold labels computed by code** from the policy rules (`src/policies/gold_engine.py`, `trust_rule.py`), never by an LLM. Each record: visible part (conversation, proposed action), hidden part (the company state), gold (decision, risk label, risk type, check needed, missing fact, required checks, policy ids).
- In-domain: **200 seeds, 482 records**, 6 domains (ACC 112, FILE 108, PRIV 94, FIN 74, REPO 66, CAL 28 records). OOD: **45 seeds, 112 records** (new CUST domain, reworded other domains, new tools).
- Case types (in-domain records): T1 hidden fact, A/B pair with the same text and opposite answer (158); T2 a tool result in the conversation: a fresh (trust it), b about another resource, c the fact changed since, d only the agent states it (164); T3 clearly safe (30); T4 clearly unsafe (38); T5 policy conflict or two facts that disagree → ESCALATE (92).
- **Splits by seed**, and seeds that share a gold policy stay in one split: train 292 records / 122 seeds, val 40 / 16, **test 150 / 62 (locked, hashed)**, **OOD 112 / 45 (locked, test only)**. Evaluation uses phase-1 tools: test 146 records; training uses 290 train records.
- History to state: test was 124 records on 30 Oct; 26 two-check T5 test records were added on 6 Nov (so test is 28% T5 vs 19% over all in-domain records: `report_extras.md` section 3).
- **Policy store:** 154 in-domain policies (170 in the OOD store), each with machine-readable logic (`data/policies/policy_logic.yaml`) and conflict pairs. **Check tools:** 28 typed read-only tools (`configs/check_tools.yaml`, 2 OOD-only), answered by the **check gateway** (`src/gateway/`) from each record's hidden state; it logs every call and enforces the call limit.
- **Label audit by code** (`label_audit.md`): every scored record rebuilds from its source, can be decided from what the monitor sees, the same policy + fact + value always gives the same decision (168 groups), test and OOD match their locks; one OOD seed (OOD-CUST-T3-002, 2 records) differs from the policy rule as the audit script reads it. **No human agreement (κ) study on our records was done** (skipped, 12 Nov).

### 4.2 Collected datasets (risk detection only) — `project_summary.md` 3.2, `collected_test_results.md`

- R-Judge 531 (369 / 47 / 115), ATBench 999 (699 / 100 / 200), AgentRisk (SemEval-2027 shared task) 617 (394 / 98 / 125). **Our own splits**, so the numbers cannot be compared with published leaderboards; ATBench was released as a test-only benchmark (PLAN Step 25.5).
- Labels mapped to our 6 risk types; ambiguous ones labelled **by hand without any LLM** (team rule). Blind double check on R-Judge risk types: κ 0.57 on 26 items (`data/labels/kappa_report.json`).
- Training list: 1,034 examples, balanced 50/50 SAFE/UNSAFE per source, privacy leakage downsampled.
- **AgentRisk has no licence: no AgentRisk text may appear in the report** (counts and scores only).

## 5. Methodology — `project_summary.md` sections 2 and 4, `docs/decisions.md`

- **Task output:** ALLOW, ASK_CONFIRMATION, BLOCK or ESCALATE, plus risk label, risk type and evidence (facts, policy numbers); or NEED_INFORMATION with the missing fact and the checks to run.
- **Four checking settings:** never (decide from the conversation), always (every check in a fixed table for the action, about 4.5-5 per record), **selective** (the model asks for the checks it wants: our method; at most 4 calls, one retry after a tool error), oracle (exactly the gold checks: upper bound).
- **Two policy conditions:** correct policies (gold + 2 look-alikes: checking and deciding as if retrieval were perfect) and retrieved policies (the full system).
- **Monitor:** Qwen3-8B (pinned revision), greedy decoding, thinking off, Kaggle 2×T4.
- **Retriever:** hybrid BM25 + `bge-base-en-v1.5`, weight 0.6, query = action + all user and agent turns. **v1:** top 3 (recall@3 0.55). **v2 (final system, 11-12 Nov):** only the policies tagged with the proposed action's tool are ranked, 8 shown (all gold policies shown: val 0.33 → 0.80, train 0.55 → 0.88).
- **v2 selective additions:** second-source check (when the model asks about a fact that two tools report, the loop adds the other tool's check) and two prompt hints (two facts → ask both; a failed check → do not repeat it). No retraining. Decided on val with a rule written before the run (`decisions.md` 2026-11-11, -12).
- **Fine-tuning:** QLoRA (rank 16, alpha 32, lr 2e-4, 2 epochs, 4-bit NF4, max 4,096 tokens), targets built by code from gold, loss on the answer only. **Phase A:** collected data only (1,034 examples): risk label + type. **Phase B (final, 10-11 Nov):** our 290 train records → 988 examples (first pass: DECISION or NEED_INFORMATION with the gold checks; second pass: the gateway's results → DECISION) + the same 1,034 collected examples = 2,022 (1,981 kept). Train loss 0.031, about 6.5 h.
- **Rule baselines:** rules only (if-then rules on facts in the conversation, never checks) and rules + environment (every table check first, then the same rules).
- **Metrics** (`docs/evaluation_metrics.md`): decision accuracy; unsafe action rate (risky records given a weaker decision); wrong-block rate; checks per record and saving vs always; check precision/recall; right missing fact; decision macro-F1; risk-label F1; risk-type macro-F1; valid JSON. 95% intervals by bootstrap over seeds (2,000 resamples); McNemar and Wilcoxon tests.
- **Hypothesis R10.4 (fixed before any result):** selective is not less safe than always: the upper end of the 95% interval of Δ unsafe (selective − always) is at most **+5 points**.
- Rigor to state: test and OOD were only run and scored; nothing was trained, tuned or chosen on them; every change was decided on val with a rule written first.

## 6. Experiment runs

- **Experiment 1 — risk detection on collected data** (mid report Table 1 + final): collected val (241): base 52.3 accuracy / 14.8 unsafe F1 / 4.0 type macro-F1; Phase A 93.8 / 93.4 / 59.6. Collected test (428), `final_report_results.md` section 9: base 54.9 / 32.8 / 26.1; Phase A 92.8 / 91.9 / 55.0; Phase B final 90.4 / 89.0 / 52.7; **word model with no LLM 88.6 accuracy** (must be shown next to the models).
- **Experiment 2 — our records, four settings** (final system v2, `final_results_v2.md`, accuracy %):

| Method | Setting | Test retrieved | Test correct | OOD retrieved | OOD correct | Val retrieved | Val correct |
|---|---|---|---|---|---|---|---|
| Rules only | never | 44.5 | 43.8 | 53.6 | 54.5 | 57.5 | 57.5 |
| Rules + environment | always | 46.6 | 52.1 | 48.2 | 54.5 | 67.5 | 65.0 |
| Base Qwen3-8B | never | 36.3 | 34.2 | 48.2 | 48.2 | 55.0 | 57.5 |
| Base | always | 54.8 | 52.1 | 58.9 | 55.4 | 80.0 | 75.0 |
| Base | selective | 44.5 | 43.2 | 50.0 | 57.1 | 65.0 | 65.0 |
| Base | oracle | 50.0 | 51.4 | 65.2 | 63.4 | 67.5 | 80.0 |
| Phase B | never | 58.2 | 61.0 | 68.8 | 67.9 | 72.5 | 75.0 |
| Phase B | always | 62.3 | 75.3 | 63.4 | 66.1 | 70.0 | 82.5 |
| **Phase B** | **selective** | **63.0** | **69.9** | **66.1** | **80.4** | **77.5** | **85.0** |
| Phase B | oracle | 80.8 | 86.3 | 82.1 | 87.5 | 90.0 | 97.5 |

  Unsafe action rate, Phase B test: retrieved never / always / selective / oracle 30.5 / 24.4 / 39.0 / 15.9; correct 29.3 / 12.2 / 39.0 / 3.7. Wrong-block rates, CIs, macro-F1, check precision/recall: `final_results_v2.md`.
- **Experiment 3 — v1 vs v2 (final_report_results.md section 3b):** selective with retrieved policies test 61.6 → 63.0, OOD 67.0 → 66.1, val 67.5 → 77.5; correct policies test 69.2 → 69.9, OOD 78.6 → 80.4. Test unsafe (retrieved): selective 52.4 → 39.0, always 34.1 → 24.4. Test oracle accuracy (retrieved) 76.0 → 80.8.
- Run counts: every model run once (one training run per adapter); Kaggle 2×T4; runs and traces kept (private), tables in `docs/reports/`.

## 7. Ablations (only what was actually run — do not invent others)

| Ablation | What changes | Result | Source |
|---|---|---|---|
| Checking setting | never / always / selective / oracle | table above; selective 0.74-0.80 checks vs 4.82 | `final_results_v2.md` |
| Policy source | correct vs retrieved policies | Phase B selective test 69.9 vs 63.0; of 48 v1 test errors that start with a retrieval miss, 12 become right with the correct policies | `final_report_results.md` 3b, 6 |
| Retriever: tag filter + 8 shown | v1 top 3 vs v2 | all gold policies shown val 0.33 → 0.80; val selective 27 → 31 of 40 | `decisions.md` 2026-11-12, section 3b |
| v2 components (val) | retrieval change only vs full v2 | 32 vs 31 of 40 (v1 27): the gain is the retrieval change; second-source never fired on val | `decisions.md` 2026-11-12 |
| Retriever: top k and filter (CPU, train+val) | k 3 / 5 / 8 / 10, with/without action filter | all gold shown 0.52 / 0.59 / 0.69 / 0.73 → with filter 0.63 / 0.74 / 0.87 / 0.89 | `improvement_suggestions.md` section 2 |
| Retriever: query form and weight | 3 query forms × 6 weights | current (action + all turns, w 0.6) best, recall@3 0.56 | same |
| Cross-encoder re-ranker | bge-reranker-base on top 20 | worse: 0.52 → 0.32 at k=3 (rejected) | `improvement_suggestions.md` section 7 |
| Training | base vs Phase B | Phase B beats base in every setting (test selective retrieved 44.5 vs 63.0) | `final_results_v2.md` |
| Training data | 30 Oct adapter vs final adapter (+42 train records, distractor turns) | never 56.7 → 70.8, oracle 81.7/84.2 → 85.0/90.0, selective 74.2 → 74.2 (same 120 test records) | `final_report_results.md` 8 |
| Phase A vs Phase B on collected data | collected-only vs all data | collected test 92.8 vs 90.4 accuracy | section 9 |
| Shortcut baseline | word model, no LLM | 88.6 on collected test: most of the base → trained jump is shared wording | `shortcut_check.md` |
| Rule baselines | rules only / rules + environment | below Phase B in every setting | `final_results_v2.md` |

**Planned but not run** (state it): ablations with no policies, check noise (the gateway supports it) and a top-k sweep on the model; Qwen3-235B comparison (dropped); live runs with two agent LLMs; v3 candidates (only the action's check tools, one more ask) built but not run (Kaggle GPU quota).

## 8. Evaluations

- **Hypothesis R10.4** (`final_report_results.md` 3b, 4; `report_extras.md` 4): Phase B v2 test +14.6 [0.0, 29.7] (retrieved), +26.8 [14.3, 39.5] (correct): fails. OOD +5.9 [−10.9, 23.3] / −3.9 [−16.4, 9.1]: fails by the rule (inconclusive). **Power:** half-width 10-17 points, so the rule could pass only if selective were clearly safer than always (observed Δ at most about −5 to −12, `report_extras.md` section 4). **Always is not safe either:** 24.4% unsafe on test with retrieved policies (v2).
- **Does it learn to ask, and the right thing?** (`check_results.md`; final adapter, system v1, correct policies, test = the original 120 records): asks when a check is needed 87.7 test / 91.5 OOD (base 53.1 / 33.8); right check among asked 81.7 / 80.0; decision right when every needed check was made 94.2 / 94.2; T2c (fact changed) asks 100% (base 0%); T5 two facts disagree: both checks made 11.8%.
- **T2 subtypes** (`final_report_results.md` 5b): Phase B selective 92-100% per subtype on test, 73-100 on OOD; already 92-100 on test without checks; base 15-85.
- **T1 pairs** (both records of an A/B pair right), test correct policies: never 1, always 10, selective 8, oracle 12 of 17; retrieved: 0 / 4 / 4 / 9 of 17.
- **Saving vs oracle saving:** test selective 83.4-84.7 vs oracle 80.0; OOD 84.9 vs 85.5. Selective makes about as many checks as needed; its 16-18 point gap to oracle on test comes from which checks it makes.
- **Error analysis** (`final_report_results.md` 6; v1): with correct policies, 22 of 45 test errors are two-check T5 records with one check made; with retrieved policies, a retrieval miss is the first cause of 48 of 56 (ceiling +7.6 points). v2: of 34 two-check test records, 10 are "one fact from two tools" (the model named another fact, so the second-source rule did not start) and 24 combine two different facts.
- **OOD by shift** (section 7): selective weaker on records with new tools (59.5 vs 71.4 retrieved, v1).
- **Cost hypotheses (exploratory, stated after the results; `cost_hypotheses.md`):** C1 check calls ≤ 0.5× always: holds (0.15-0.17×). C2 tokens ≤ 0.5×: does not hold (about 2.4×: the prompt lists every tool, 1.6-1.8 passes per record); cheaper overall only where a check call costs more than about 350-400 tokens. The proposal had already said selective "may use more tokens or time; its gain may be fewer checks and less access to private data rather than lower cost". C3 accuracy within 5 points of always: not shown on test. C4 beats rules + environment: holds on test (+16-18 points).
- **Reweighted test** (`report_extras.md` 3): test reweighted to the in-domain case-type mix: v1 selective 66.3 / 74.3 instead of 61.6 / 69.2; the raw number stays the main result.

## 9. Limitations (`final_report_results.md` section 10)

- Small sets (40 / 146 / 112); wide intervals (about ±10 points on test accuracy); OOD has 51 risky records.
- Test grew after the 30 Oct run (26 two-check T5 records): more T5 than the data overall.
- Generated records; labels from our own rules, checked by code only; **no human agreement study** on our records; the only κ is 0.57 on 26 R-Judge risk types.
- One training run per adapter: run-to-run variance unknown.
- Accuracy counts BLOCK-for-ESCALATE as wrong (both stop the action): counting that as acceptable, always 75.3 → 89.0 and selective 69.2 → 72.6 (test, correct, v1).
- Two-check cases that combine different facts are not learned (only one mechanism in train).
- Selective costs more model tokens than always.
- Collected datasets: our own splits, shortcuts (word model 88.6; 43 R-Judge near-copies).
- Not done: service, demo and live runs with two agent LLMs (empty in the repo); planned ablations; v3 val check; 50 evidence hand-checks.

## 10. Conclusions

1. Fine-tuning teaches an 8B model to monitor agents with checks: Phase B beats base and both rule baselines everywhere, and carries over to a new domain (OOD).
2. Selective checking needs about one sixth of the check calls of always, and the model learns when to ask and mostly what to ask (94% right when it has every needed check).
3. It is **not** as safe as always checking on in-domain test, mainly because it makes one check when two are needed.
4. Tag-filtered retrieval (v2) made the system safer without retraining; the remaining gains need new two-check training data (several mechanisms), a second training seed and a human label study.
5. Report the negative result as it is: both answers were said to be useful in the proposal.

## 11. References

The proposal's list (`docs/Catalysts.pdf`, page 8), with the ATBench fix:

- AgentRisk organizers. SemEval-2027 AgentRisk shared task. https://agentrisk-semeval.lovable.app/, accessed October 2026.
- M. Andriushchenko et al. AgentHarm: A benchmark for measuring harmfulness of LLM agents. ICLR, 2025.
- Z. Chen et al. ShieldAgent: Shielding agents via verifiable safety policy reasoning. ICML, 2025.
- J. Cohen. A coefficient of agreement for nominal scales. Educ. and Psych. Measurement, 20(1):37–46, 1960.
- J. R. Das. pi-bench: A stateful policy-compliance benchmark for tool-using agents. https://github.com/Jyoti-Ranjan-Das845/pi-bench, 2026.
- T. Dettmers et al. QLoRA: Efficient finetuning of quantized LLMs. NeurIPS, 2023.
- Y. Geifman and R. El-Yaniv. Selective classification for deep neural networks. NeurIPS, 2017.
- E. J. Hu et al. LoRA: Low-rank adaptation of large language models. ICLR, 2022.
- Hu et al. SABER: Benchmarking operational safety of LLM coding agents in stateful project workspaces. arXiv:2606.01317, 2026.
- H. Inan et al. Llama Guard: LLM-based input-output safeguard for human-AI conversations. arXiv:2312.06674, 2023.
- P. Lewis et al. Retrieval-augmented generation for knowledge-intensive NLP tasks. NeurIPS, 2020.
- Li et al. ATBench. arXiv:2604.02022, 2026. (**Full title and authors to confirm**; PLAN Step 25.6.)
- Liu et al. AgentDoG: A diagnostic guardrail framework for AI agent safety and security. arXiv:2601.18491, 2026.
- W. Luo et al. AGrail: A lifelong agent guardrail with effective and adaptive safety detection. ACL, 2025.
- Qwen Team. Qwen3 technical report. arXiv, 2025.
- Y. Ruan et al. Identifying the risks of LM agents with an LM-emulated sandbox. ICLR, 2024.
- H. Shim, S. J. Hwang, and E. Yang. Joint active feature acquisition and classification with variable-size set encoding. NeurIPS, 2018.
- A. D. Tur et al. SafeArena: Evaluating the safety of autonomous web agents. ICML, 2025.
- S. Vijayvargiya et al. OpenAgentSafety: A comprehensive framework for evaluating real-world AI agent safety. arXiv:2507.06134, 2025.
- Yan et al. Trust No Tool: Evaluating and defending LLM agents under untrusted tool feedback. arXiv:2605.17453, 2026.
- T. Yuan et al. R-Judge: Benchmarking safety risk awareness for LLM agents. Findings of EMNLP, 2024.
- Z. Zhang et al. Agent-SafetyBench: Evaluating the safety of LLM agents. arXiv:2412.14470, 2024.
- To add if verified: PhantomPolicy/Sentinel, Ask the World Before Acting, MIRAGE; the bge embedding and re-ranker models; BM25.
