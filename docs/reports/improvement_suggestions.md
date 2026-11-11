# Improvement suggestions: a review of the Agent-Risk monitor

Reviewer run on 11 Nov 2026 (3 days before the 14 Nov deadline). Nothing was changed except this file; no GPU job was run; test and OOD record text was not read. Every number is from a committed report or from the CPU analyses in section 2, which read **train and val records only**.

**One correction to the brief.** The brief says retrieval misses "cause" 48 of 56 test errors. That is the first-cause grouping of `src/eval/error_analysis.py` (a record whose policy was missing is counted there even if the model would also have failed the check). The real ceiling of a perfect retriever is the gap between the two policy conditions: Phase B selective goes from 61.6 to 69.2 on test (56 to 45 errors, **+7.6 points**), 67.0 to 78.6 on OOD (+11.6), 67.5 to 82.5 on val (+15.0) (`docs/reports/final_results.md`, Phase B selective rows in the four test/OOD sections). Retrieval is still the largest single lever, but it is worth about 8 points on test, not 30. With correct policies the largest error group is the two-check T5 records (22 of 45 test errors, `error_analysis_test.md:146`), and that is a checking problem.

## 1. Ranking

Score = expected gain x confidence / cost, judged by hand. "Gain" is on the final-run metrics for the full system (Phase B, selective, retrieved policies) unless stated. GPU hours are Kaggle T4 x2.

| # | Suggestion | Area | Expected gain | Confidence | Cost (people / GPU) | Score | When |
|---|---|---|---|---|---|---|---|
| S1 | Action tags on the policy store, retriever filters by the proposed action's tool, show 8 policies | A | all gold policies shown 0.52 -> 0.87 (train+val); test accuracy about +5, OOD about +9, val up to +12 | high (recall measured), medium (downstream) | 5 h / 0.5 h val check + 10 h final rerun | high | **before 14 Nov** |
| S2 | Second-source completion: when the model asks about a fact that two tools answer, the loop adds the sibling call; plus one prompt line | E | test unsafe rate (correct policies) 41.5 -> about 30; Δ unsafe +29 -> about +17 (motivated by test evidence) | medium | 3 h / 0.5 h + shared rerun | high | **before 14 Nov** |
| S3 | Report fixes: per-case-type headline, test composition shift, retrieval ceiling, power of the hypothesis test, cost-safety curve, single-run caveat | F | no metric change; prevents a misleading report | high | 4 h / 0 | high | **before 14 Nov** |
| S4 | Show only the check tools in the action's check_table rows (28 -> about 3-7 tools) | E | wrong-tool errors down (10 of 45 test errors with correct policies, 8 of 11 CUST OOD errors); prompt -800 tokens | medium | 2 h / shares the val check | medium | before 14 Nov if the val check passes |
| S5 | Retry hint after a gateway error | E | 2-4 test records, 3-4 OOD; call error rate 5-11% -> lower | high (small) | 1 h / 0 | medium | before 14 Nov |
| S6 | Human audit of the 31 unreviewed seeds and the κ study on our records (gate G3) | C | credibility; may find wrong gold | high | 6-8 h humans / 0 | medium | before 14 Nov (report), fixes later |
| S7 | Second-pass training examples with the full table results (what "always" sees) | B/D | always accuracy +5-10 (test, correct policies); robustness when selective over-asks | medium | 2 h / 6.5 h retrain + 10 h rerun | medium | future (needs a retrain) |
| S8 | Two-check training data with new mechanisms (train-only composite policies, 8+ seeds), oversample two-check examples | B | both-checks rate 12% -> maybe 40-60%; T5 accuracy up | low-medium | 8-12 h humans / 6.5 h + 10 h | medium | future |
| S9 | Allow a second NEED_INFORMATION pass when budget remains | E | small; the model never trained for it | low | 1 h / shares the val check | low-medium | optional, before 14 Nov |
| S10 | Second training seed of the final adapter (variance estimate) | F | tells run noise from real change (asks-when-needed fell 97.5 -> 87.7 between adapters) | medium | 0.5 h / 6.5 h + 5 h | low-medium | future |
| S11 | Cross-encoder re-ranker on the top 20 | A | **negative**: 0.52 -> 0.32 at k=3 in the CPU trial (section 7) | high (measured) | 2 h / 0 | rejected | never |
| S12 | DPO on one-check vs two-check pairs from train records | D | both-checks rate up | low | 6 h / 1 h + 2 h + 10 h | low | future |
| S13 | NEED_INFORMATION target with one `missing_fact` per check | D | removes a one-fact bias in the format | low | 2 h / retrain | low | future |
| S14 | Align the training look-alikes with the evaluation query (last turn, w 0.5 vs all turns, w 0.6) | D | hygiene | high (small) | 0.5 h / with the next retrain | low | with the next retrain |

### Do before 14 Nov (at most 3)

1. **S1: tagged retrieval with 8 policies.** Inference-only, measured on train+val, biggest ceiling. Check on val with the final adapter (selective, retrieved: about 25 minutes), then rerun the final jobs (base and Phase B on val, test and OOD: about 5 h each in the two slots, one night). Add a Changelog row to `docs/decisions.md` (changes R8.1 and the top-3 rule). Keep the text-only retriever numbers in the report as the comparison.
2. **S2 + S5 (+ S4 if the val check does not hurt):** second-source completion, retry hint, and the filtered tool list. All inference-only, all in the same val check and the same final rerun as S1. Add a Changelog row (R9.4, R9.5: "selective" = the model's request plus the deterministic completion rule).
3. **S3:** report fixes. No GPU. Do them whatever happens with 1 and 2.

Do **not** retrain again before 14 Nov. One more Phase B run is physically possible (12 Nov night) but there is no way to tell a better adapter from run noise with one run (S10), the val set cannot judge the T5 changes (section 6), and a worse adapter 24 hours before the deadline cannot be undone. S7, S8, S13, S14 go into the next retrain as a package.

## 2. What I ran (CPU, train + val only)

`src/policies/retriever.py` with the evaluation query (`query_for(all_turns=True)`, `EVAL_W` 0.6), on the 332 train + val records, in-domain store (154 policies). "all" = every gold policy in the top k (what a T5 conflict needs).

Query form and weight (recall@3, at least one gold policy):

| Query | w 0.0 | 0.3 | 0.5 | **0.6** | 0.8 | 1.0 |
|---|---|---|---|---|---|---|
| action + all user and agent turns (current) | 0.48 | 0.52 | 0.55 | **0.56** | 0.53 | 0.45 |
| action + last user turn | 0.42 | 0.45 | 0.51 | 0.49 | 0.48 | 0.44 |
| action only | 0.40 | 0.44 | 0.45 | 0.44 | 0.45 | 0.39 |

The current query and weight are already the best of these; there is little left in query wording.

Top k, current retriever, and the same with the policy list first **filtered to policies tagged with the proposed action's tool** (tags taken from `data/policies/policy_logic.yaml` `actions`, only to measure what tagging could give; every gold policy carries its record's action, 0 mismatches):

| k | all gold shown | T1 | T2 | T3 | T4 | T5 | with action filter: all | T1 | T2 | T3 | T4 | T5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 0.52 | 0.44 | 0.56 | 0.80 | 0.79 | 0.38 | **0.63** | 0.61 | 0.61 | 0.95 | 0.86 | 0.48 |
| 5 | 0.59 | 0.46 | 0.66 | 0.95 | 0.86 | 0.48 | **0.74** | 0.69 | 0.76 | 1.00 | 0.86 | 0.68 |
| 8 | 0.69 | 0.57 | 0.75 | 1.00 | 0.89 | 0.58 | **0.87** | 0.80 | 0.97 | 1.00 | 0.89 | 0.76 |
| 10 | 0.73 | 0.64 | 0.78 | 1.00 | 0.93 | 0.66 | **0.89** | 0.82 | 0.99 | 1.00 | 0.93 | 0.76 |

- T5 conflicts (22 records with 2 gold policies): both policies in the top 3: 0.41, top 5: 0.50; with the filter 0.59 and 0.82.
- Gold policies ranked beyond 10 by the text retriever: T1 44 of 122, T2 25 of 112, T5 17 of 72, T3 0, T4 2. For T1 the deciding fact is hidden by design, so the policy's words (legal hold, last admin, clearance) are not in the conversation: no text query can find them. Tags can.
- Policies tagged per record: mean 15.5, median 17, max 27 (grant_permission). A policy line is about 16 tokens; the prompt is about 1,680 tokens with 3 policies, 1,766 with 8, 1,893 with 16. The 28-tool list costs about 990 tokens.
- By domain (recall@3, current): CAL 0.95, ACC 0.70, REPO 0.65, PRIV 0.48, FIN 0.43, FILE 0.39.

Data facts used below (train + val): 26 two-check records in train (13 seeds) and 2 in val, **all 26 train ones use the same mechanism** (`account_type`, tool pairs `check_recipient_type` + `check_user_authorization` 22, + `check_transfer_compliance` 6). `configs/fact_checks.yaml` lists 3 of 60 facts with more than one tool: `account_type` (3 tools), `modifiable` (2), `role_eligible` (2). Train check-needed records: 178 with one check, 26 with two, so 52 of the 408 first-pass NEED_INFORMATION training examples (13%) show two checks. 31 of 200 in-domain seeds have `reviewer: TBD` (ACC-T5 7, FILE-T5 5, PRIV-T5 4, FIN-T5 3, REPO-T5 3, ACC-T2 3, others 6); 195 of 200 seeds have one author.

Case-type composition (share of records): T5 is 16% of train, 5% of val, **28% of test**, 11% of OOD, 19% of all in-domain; two-check records are 9% of train, 5% of val (2 records), **23% of test**, 2% of OOD. Risky records (gold not ALLOW): train 51%, val 48%, test 55%, OOD 46%.

## 3. Suggestions in detail

Each item: problem and evidence, change, expected effect, confidence, cost, risks, validation without test/OOD, timing.

### A. Policy retrieval

**A1 = S1. Tag policies with the actions they govern; filter by the proposed action; show 8.**

1. *Problem.* recall@3 0.55 (`src/policies/retriever.py:19` comment; measured 0.56 above); the full system loses 7.6 test points, 11.6 OOD points and 15 val points to retrieval (section 0). PLAN Step 6 asked for recall@3 ≥ 0.9 and said "if it is lower, improve the query text before moving on" (`docs/PLAN.md`, Step 6 "Done when"); the query is already the best of the forms tried.
2. *Change.* (a) Add an `applies_to: [tool names]` field to each line of `data/policies/policies.jsonl` and `policies_ood.jsonl`, generated by `scripts/gen_policy_store.py` from the same seed information that produces `policy_logic.yaml` `actions`, then **confirmed by a human from the visible text** (154 + 170 lines, about 2 h; see C3). (b) In `Retriever.rank` (`retriever.py:87-110`) score only policies whose `applies_to` contains `visible.proposed_action.name` (fall back to all policies if none is tagged, e.g. a new tool). (c) `N_SHOWN = 8` in `src/monitor/case_inputs.py:21` and `TOP_K` in `retriever.py:20`; `build_sft.N_POLICIES` (`build_sft.py:48`) to 8 at the next retrain so training and evaluation match. (d) R8.1 Changelog row: the retriever reads visible policy text plus the `applies_to` metadata, not the hidden logic.
3. *Expected effect.* All gold policies shown 0.52 -> 0.87 on train+val (0.63 with tags at k=3; 0.69 with k=8 alone). Downstream ceiling is the correct-policies result: test selective 61.6 -> at most 69.2, OOD 67.0 -> at most 78.6, val 67.5 -> at most 82.5. With 0.87 recall and 5 extra distractor policies, a fair estimate is test +5, OOD +8 to +9, val +10 to +12, for every setting (always and never gain too). Checks per record unchanged.
4. *Confidence.* High that recall rises (measured on 332 records). Medium that the model handles 8 policies as well as 3 without retraining: it was trained with 3 (gold + 2 look-alikes), and more look-alikes could cause wrong blocks (test wrong-block is 7.8% now, `final_results.md:71`).
5. *Cost.* Code and tests 3-4 h; human tag confirmation 2 h; val check 25 min GPU (Phase B, selective, retrieved, 40 records); final rerun 2 x 5 h GPU in parallel.
6. *Risks.* (i) The tags come from the generator, the same source as the gold logic. A reviewer can say retrieval is "told" which policies matter. Mitigation: the human confirmation step, and the report shows text-only and tagged retrieval side by side, with the tags described as the "applies to" field a real policy store has. (ii) Prompt +90 tokens: negligible. (iii) k=8 with tags still misses 13% (T1 0.80, T5 0.76): the remaining misses are policies whose text does not match the story at all; only showing every tagged policy (mean 15.5, 100% by construction, +215 tokens) removes them, but that is a bigger change to what the model sees and should wait for a retrain.
7. *Validation.* Recall on train+val (done above; redo after tagging). Then one val run with the final adapter, selective and always, retrieved policies with k=8 and tags: compare accuracy, wrong-block and asks-when-needed with the current val numbers (67.5 / 70.0 accuracy, `final_results.md:20-21`). Accept if val accuracy does not fall and wrong-block does not rise by more than 2 records. Nothing in this touches test or OOD until the final rerun.
8. *Timing.* Before 14 Nov: code 11 Nov evening, val check 12 Nov morning, final rerun 12 Nov night, tables 13 Nov.

**A2. Show every tagged policy (no top-k) at the next retrain.** Same as A1 but the model sees all policies for the action (mean 15.5, max 27; +215 tokens). Recall 1.0 by construction; the model must pick the right one among 15. Needs retraining with the same input (6.5 h) and is the right end state. Future work, with S7/S8/S13/S14 in one retrain.

**A3 = S11. Cross-encoder re-ranking of the top 20. Rejected after a CPU trial** (section 7): `BAAI/bge-reranker-base` over the current top 20 gives 0.32 at k=3 against 0.52 without it, and 0.44 against 0.63 after the action filter; worse in every case type. The brief's suggestion (A, "a cross-encoder re-ranker on the top 20") does not hold for one-sentence policies and conversation-length queries. Do not implement.

**A4. Retrieving both sides of a conflict.** Covered by A1: both conflict policies in the top 5 go from 0.50 to 0.82 with the filter. No separate change needed; report "both policies shown" for T5 as PLAN Step 6.4 asked.

**A5. Learned dense retriever (fine-tune bge on query -> gold policy pairs from train).** Rejected for now: policies are split-disjoint by design (`decisions.md` 2026-10-27 row: "seeds that share a gold policy stay in one split"), so a retriever trained on train pairs learns the 100-odd train policies and is tested on policies it never saw as positives. With 292 train queries it would mostly memorise wording. Future work only with a much larger policy set.

**A6. Query wording.** Rejected: measured above, the current form is the best of three and w is flat between 0.5 and 0.6. Adding the acting user's team or the resource kind to the query is not supported by the hidden-fact problem (T1: 44 of 122 gold policies beyond rank 10 for a reason no query fixes).

### B. Training data

**B1 = S7. Second-pass examples with the full table results.**

1. *Problem.* `build_sft.our_examples` (`src/training/build_sft.py:124-139`) builds the second pass from the gold `required_checks` only, so the model never trained on irrelevant check results. The always setting shows 4.5-5 results, most irrelevant: with correct policies on test, always has 30 "right fact, wrong decision" errors against 20 for oracle (`error_analysis_test.md`, "By model" table, Phase B gold always vs oracle); on the 26 new T5 records always gets 10 of 26, oracle 18 of 26 (`check_results.md:62-68`, and section 5.3 of `final_report_results.md`); on OOD always blocks 27.9% of safe records vs oracle 9.8% (`final_results.md`, OOD gold section). Within selective, the 7-10 "wrong fact" errors per split are cases where an extra fact confused the decision.
2. *Change.* For every check-needed train record add a third example kind (b'): the first-pass prompt plus the results of **all** `table_calls(action)` (what always sees), target = the gold DECISION; for every no-check record add the same with target = its DECISION. Keep (b) as it is. REPEAT_OURS stays 2 for (a) and (b); 1 for (b').
3. *Expected effect.* always accuracy +5 to +10 on test with correct policies (30 right-fact-wrong-decision errors is the pool); OOD always wrong-block down; selective's "wrong fact" errors down a little. Side effect: a stronger always makes the R10.4 comparison harder, not easier; that is the honest direction.
4. *Confidence.* Medium-high for always (the training distribution gap is clear); low for selective.
5. *Cost.* 2 h code + tests; +about 300 training examples (+15% training time); retrain 6.5 h; final rerun 10 h.
6. *Risks.* The model might start ignoring facts in general; watch oracle accuracy on val (97.5 now).
7. *Validation.* val always and oracle runs with the new adapter (40 records; 2 x 10 min GPU) vs 82.5 / 97.5 now.
8. *Timing.* Future (needs a retrain).

**B2 = S8. Two-check training data with more than one mechanism.**

1. *Problem.* All 26 train two-check records (13 seeds) use `account_type`; the model makes both checks in 12% of two-check test records and 2 of the 26 new ones (`check_results.md:62-68`, "Every needed check" 7.7). The test two-check records use six other mechanisms (Param's note `docs/messages/2026-11-06_to_Meet_t5_facts_disagree_seeds.md`: modifiable, registered_vendor, recipient_class, role_eligible, exposure, disposable; I did not read the records). The model learned "account_type needs two tools", not "when a policy depends on two facts, or a fact has two sources, ask for both". Motivated by test evidence; the train-side fact (one mechanism) is verifiable on train alone.
2. *Change.* Param writes **train-only** composite policies (two facts must agree) in FILE, REPO, FIN and PRIV, each with 2-3 seeds (A/B: facts agree -> ALLOW or BLOCK by the rule, facts disagree -> ESCALATE), so that at least 4 mechanisms and 16+ records exist in train; gold computed by `gold_engine` + `conflicts.yaml` as now. In `build_sft`, repeat two-check first-pass examples 4x instead of 2x (`REPEAT_OURS`, `build_sft.py:47`, made per record). `make records` + `auto_checks` + `leakage_check` as for the 6 Nov seeds.
3. *Expected effect.* Both-checks rate from 12% to perhaps 40-60% on unseen mechanisms; each two-check record that gets both facts has about a 70% chance of the right ESCALATE (oracle 18 of 26). On a test like the current one that is up to +8 accuracy points and -10 unsafe points, but **the estimate rests on one adapter and 26 records**.
4. *Confidence.* Low-medium: the 6 Nov addition (10 -> 26 two-check train records) did not move the both-checks rate between the 30 Oct and final adapters (both about 12%), so more of the same mechanism will not help; new mechanisms might.
5. *Cost.* Humans 8-12 h (policies + seeds + review); retrain 6.5 h; rerun 10 h. Reopens the 8 Nov data freeze: needs a Changelog row and the team's agreement.
6. *Risks.* New policies must not share wording with test-only policies (the near-duplicate check exists, `split.py`); more ESCALATE examples may raise ESCALATE on one-check records (wrong block).
7. *Validation.* Hold out 2 of the new seeds (4 records) as a dev set that never enters training; plus the model's both-checks rate on the 26 train two-check records (optimistic, the model saw them). Val cannot help (2 two-check records).
8. *Timing.* Future. If the team insists on a last retrain, this is the one data change to include, but it needs the data by 12 Nov noon.

**B3. Hard negatives and counterfactual pairs.** T1 already gives A/B pairs with identical text (R11.1). The generator could add, for each check-needed record, a sibling where the check result is the *other* value (already the A/B design) and one where a **non-deciding** table fact is risky-looking but the policy does not cover it (teaches "a fact no shown policy is about is ignored", which the rule baseline encodes explicitly, `src/baselines/rules.py:7-10`). This is B1 in data form; do B1 first (no human writing needed).

**B4. New-tool coverage.** OOD selective on new-tool records 59.5 vs 71.4 on reworded ones (`final_results.md`, "OOD by kind of shift"). The 24 phase-2 train records added on 10 Nov cannot be measured (no val or test record uses those tools). Future: a small phase-2 dev set (6 seeds, never trained on) so the next retrain can show whether tool variety in training helps new tools.

**B5. Distractor turns.** 18 train records contain a tool-error turn as a distractor (Param, 6 Nov). Their effect cannot be measured either (no val/test record has the cue; `shortcut_check.md`). Keep; do not add more until the perturbation test (section 5 of `final_report_results.md`, "not done") exists.

### C. Labelling (humans only, no LLM)

**C1 = S6a. Review the 31 unreviewed seeds.** `reviewer: TBD` on 31 of 200 in-domain seeds, 22 of them T5 (the case type where the gold ESCALATE depends most on judgment) and 195 of 200 seeds by one author. A second person reads each seed's story, policies and facts and answers: is the scenario realistic, does the stated decision follow from the policy text a monitor can see, is "two facts disagree -> ESCALATE" the right call or should it be BLOCK? Record disagreements in a CSV. Changing a locked test seed needs `split --relock` and a Changelog row (R11.3); if there is no time to rerun, report the disagreement count as a limitation instead. 4 h for one reviewer.

**C2 = S6b. κ study on our records (PLAN gate G3, not met).** No agreement study exists for our own gold yet (the R-Judge one gave κ 0.57, below 0.6, `data/labels/kappa_report.json`). 30 records: two people see the visible text, the shown policies and the gold facts (not the gold decision) and give decision + risk type; report κ per field. It is assigned to Param and Moiesha for 11 Nov in `PROGRESS.md`; it is a report requirement, not a result changer. 3 h for two people.

**C3. Confirm the policy action tags (for A1).** 154 + 170 policy lines: does the policy text apply to the listed tools? About 2 h. This makes A1 defensible as metadata rather than generator leakage.

**C4 = S32. ESCALATE vs BLOCK on facts that disagree.** With both facts, the model says BLOCK instead of ESCALATE on 7 of 26 new T5 records (section 5 of `final_report_results.md`); BLOCK ranks equal to ESCALATE for safety (`metrics.py:17`) but counts as wrong in accuracy and in "right fact, wrong decision". Humans should decide, and the report should say, whether BLOCK is an acceptable operator outcome when facts disagree (a human reviews either way). Report accuracy both ways. No label change; 1 h.

**C5. 50 evidence hand-checks.** Planned (PLAN 23.4, `src/eval/error_analysis.py --evidence-sheet`), owner still "to choose". Make the sheet from the final runs; two people; no LLM. 3 h.

### D. Training method

**D1 = S13. One `missing_fact` per check.** `FORMAT_NEED_INFO` (`prompt_builder.py:21-23`) has one `missing_fact` and 1-2 checks; the two-check targets write one fact with two tools (`build_sft.need_information_target`, `build_sft.py:107-111`). A `missing_facts` list, one entry per check, and the instruction "list every fact the decision needs; a fact that two tools report needs both" make the two-check case a first-class format instead of an exception. Needs a retrain and a parser change (`src/monitor/parser.py`). Low confidence on its own; do it together with B2.

**D2 = S12. Preference training (DPO) on one-check vs two-check.** Run the final adapter on the 26 train two-check records (first pass only, 20 min GPU), keep the one-check outputs as "rejected" and the gold two-check NEED_INFORMATION as "chosen", DPO for one epoch with TRL (in `requirements.txt`). 26 pairs is very few; with B2's new seeds it becomes 40-50. Low confidence; future.

**D3. Loss weighting, epochs, rank, learning rate.** No evidence for any direction: eval loss is flat across the two epochs (0.024 -> 0.025, `outputs/kaggle/finetune_final/results/train_stats.json`), there is one run per configuration, and each run costs 6.5 h. Rejected before the deadline; a val-based sweep is future work and needs S10 first (run-to-run noise).

**D4. Multi-task weighting with the collected data.** The collected examples are 51% of training (1,034 of 2,022). Collected val F1 moved 91.5 -> 91.1 between adapters; our val moved 85.0 -> 82.5 (correct policies, selective): no sign that either side drowns the other. Rejected for now.

**D5. Training on the retrieval condition.** Showing the actual top-k in training is tempting, but when the deciding policy is missing the gold decision is not derivable from the prompt, so the target would teach guessing. Rejected. The variant "target = ASK_CONFIRMATION when the deciding policy is missing" changes the task and does not help the safety metric (rank 1 is still "let through" against a BLOCK gold, `metrics.py:58-62`).

**D6 = S14. Align training look-alikes with the evaluation query.** `build_sft.shown_policies` picks look-alikes with `query_for(rec["visible"])` (last turn) and `Retriever(policies)` at `DEFAULT_W` 0.5 (`build_sft.py:119`, retriever.py:16), while evaluation uses all turns and w 0.6 (`case_inputs.py:43`). Harmless but pointless difference; fix at the next retrain (one line each).

### E. Prompt and inference

**E1 = S2. Second-source completion rule + one prompt line.**

1. *Problem.* On two-check records the model asks (94%) but makes both checks in 12% (test, 34 records) and 2 of 26 on the new ones; it then sees one normal-looking fact and allows (`check_results.md:62-68, 71-90`). The loop gives it exactly one chance: after the first NEED_INFORMATION a second ask is allowed only after a tool error (`loop.py:65-66`). Motivated by test evidence (val has 2 two-check records).
2. *Change.* In `_selective` (`loop.py:55-68`), after parsing a NEED_INFORMATION: for every requested call `(tool, args)`, look up the facts that tool returns (`configs/check_tools.yaml` `facts`, already indexed in `configs/fact_checks.yaml`); for each such fact with another tool in `fact_checks.yaml` that has a row for the proposed action in `configs/check_table.yaml`, add that tool's call with the same resource (args from the table row). Stay within `MAX_GATEWAY_CALLS`. Log the added calls with `"added_by": "second_source"` so the report can count them. Prompt (`prompts/monitor_v1.txt` trust rule, or the checks section at `prompt_builder.py:125`): add "If a policy depends on two facts, or two tools report the same fact about the resource, ask for both. If two results disagree, ESCALATE." Changelog rows for R9.4/R9.5.
3. *Expected effect.* The rule fires for the 3 multi-tool facts (`account_type`, `modifiable`, `role_eligible`), i.e. every train two-check record and the test mechanisms built on these facts; composite-policy mechanisms (two different facts) are reached only by the prompt line, which is weaker. Where both facts arrive, the decision is right about 70% of the time (oracle 18 of 26). Rough test estimate: 8-12 of the 20 "incomplete check" unsafe records fixed -> unsafe rate with correct policies 41.5 -> about 30, Δ unsafe +29 -> about +17 (still fails the ≤ +5 rule); checks per record +0.1 to +0.2 (on about 15% of records). With retrieved policies the gain is smaller (the policy is often missing too).
4. *Confidence.* Medium: the mechanics are deterministic; the decision quality with both facts is measured (oracle); the share of test mechanisms covered by multi-tool facts is not known to me (I did not read test records) and may be only 2 of 6.
5. *Cost.* 3 h code + tests (a unit test per multi-tool fact), shared val check, shared final rerun.
6. *Risks.* It is no longer "the model asks for the checks it wants": the report must define selective as model request + completion rule and show checks per record with and without it. Extra calls on records that need one check (precision drops a little). The prompt line is a change after training; small text additions have been fine before (R9.7 example fix) but the asks-when-needed rate must be watched on val.
7. *Validation.* (i) Unit tests on the rule. (ii) The 26 train two-check records with the final adapter, selective, correct policies: both-checks rate and ESCALATE rate before/after (optimistic: trained on them, 15 min GPU). (iii) val selective run: asks-when-needed (82.1 now), checks per record (0.70), accuracy (82.5 correct / 67.5 retrieved) must not fall. Val's 2 two-check records use `recipient_class`, which is not a multi-tool fact, so the rule will not fire on val: say so in the report.
8. *Timing.* Before 14 Nov, in the same rerun as A1.

**E2 = S4. Show only the action's check tools.** `render_tools` shows all 28 tools (about 990 tokens, `prompt_builder.py:94-100`). Every gold check is a `check_table` tool for the record's action by construction (`configs/fact_checks.yaml` header; `gold.required_checks` are filled from table rows), so filtering the list to `check_table[action]` (mean 3.1, max 7; `table_calls` in `src/gateway/gateway.py:196` already resolves them) never hides the right tool and removes most wrong choices: 10 "wrong fact" errors on test with correct policies (`error_analysis_test.md:146` and T1 row), 8 of 11 CUST errors on OOD (`error_analysis_ood.md`, gold section, CUST row). Risk: trained with the full list; a shorter list is an easier prompt, not a different format. OOD-only tools must be included for OOD records (they are in the OOD table rows). Validate on val: right-check-among-asked 73.9 (correct) / 45.5 (retrieved) (`check_results.md:40-60`) and asks-when-needed. 2 h. Before 14 Nov if the val check passes; otherwise with the next retrain (train with the filtered list too).

**E3 = S5. Retry hint.** After a gateway error the retry prompt shows the error JSON and the same tool list (`build_decide_prompt`, `prompt_builder.py:109-140`). The model repeated the identical failing call on 3 test records (two `check_user_clearance` not_found, two `check_owner_approval` not_found; `error_analysis_test.md`, wrong records list; test evidence) and errors are 5-11% of calls on val and OOD (`check_results.md:43-60`). Add to the retry prompt: "The call above failed (`not_found` / `invalid_args`): the name or the argument is wrong, or the tool does not cover this resource. Choose a different tool or argument; do not repeat the same call." 1 h; validate on val call-error rate. Before 14 Nov.

**E4 = S9. Allow a second ask when budget remains.** `MAX_PASSES` 3 and 4 calls already leave room; `may_check` is true after the first ask only when a call failed (`loop.py:65-66`). Allowing one more NEED_INFORMATION when `room` is true lets the model ask for the second source after seeing the first result. But second-pass training examples are DECISION-only (`build_sft.py:139`), so the adapter may never use it; the prompt would need "you may ask once more". Low confidence, 1 h, cheap to include in the val check; only keep it if val shows asks on the second pass.

**E5. Always-check for high-risk action types.** A cost-safety knob: run the table checks for `transfer_money`, `delete_repository`, `delete_file` and the model's own checks elsewhere. It is a different operating point, not a model improvement; report it as a point on a **cost-safety curve** (unsafe rate vs checks per record for never, selective, selective + E1, this hybrid, always, oracle). Cheap to compute from existing runs for the pure settings; the hybrid needs a run. Optional.

**E6. Self-consistency / strictest of k samples.** Rejected before the deadline: 5x inference (a 5 h job becomes 25 h), and taking the strictest decision raises wrong blocks as it lowers unsafe. Future, as a point on the curve.

**E7. Confidence-based escalation.** Rejected: no calibrated confidence from a greedy JSON answer; adding log-prob thresholds is a new untested component.

### F. Evaluation

**F1 = S3a. Test composition and the headline.** The 6 Nov addition put 13 of 21 new T5 seeds in test: test is 28% T5 and 23% two-check records, against 16% / 9% in train, 5% / 5% in val and 19% / 13% over all in-domain records. Two-check records are the model's worst case (accuracy 3.8-7.7 on the new 26). The headline numbers therefore understate the model relative to the data it was built for, and val (2 two-check records, both the train mechanism) cannot predict any of this. Report per-case-type results and one line that reweights test to the in-domain case-type mix; keep the raw number as the primary. No GPU.

**F2 = S3b. What the hypothesis test can show.** The Δ unsafe intervals are about 26 points wide on test (83 risky records, bootstrap by 62 seeds) and 26-30 on OOD (51 risky). With a 5-point margin the test can pass only if selective is at least about 8 points **safer** than always. The pre-registered rule must stay (changing it after the results would be tuning), but the report should say what the power was, and add: absolute unsafe rates, the gap to oracle, and the cost-safety curve (E5). Also note that the always reference is not "safe": 34.1% unsafe on test with retrieved policies (`final_results.md:70`), because it blocks on non-deciding facts and inherits retrieval misses.

**F3 = S3c. Retrieval ceiling.** State the correction from section 0 (first-cause counts vs the correct-policies ceiling) wherever "retrieval causes most errors" appears (`final_report_results.md` sections 2 and 6, `PROGRESS.md`).

**F4 = S10. Run-to-run variance.** One training run per adapter (R13.1). Asks-when-needed fell 97.5 -> 87.7 (test) and 97.2 -> 91.5 (OOD) between the 30 Oct and final adapters while accuracy barely moved (`check_results.md:41-46`); nobody can say whether that is the data change or the seed. A second training seed of the final configuration (6.5 h + 5 h eval) would give the only variance estimate the project has. If GPU time is free after the final rerun, this is a better use of it than any blind hyperparameter change. Report "single run" as a limitation either way.

**F5 = S31. Choosing on 40 val records.** A 40-record val set has a ±15-point accuracy interval; it can reject a change that breaks the model, not pick between two similar ones. Cross-validation over train seeds (5 folds x 6.5 h = 32 h GPU) is future work; a single held-out dev set of about 20 train seeds (never trained on) is the cheap version for the next iteration. For the pre-deadline changes (A1, E1-E3) use val as a safety check plus the train-side measurements above, and say that this is what was done.

**F6 = C4. Safety-weighted accuracy.** BLOCK for a gold ESCALATE (and the reverse) is a wrong decision but not an unsafe action (both rank 2, `metrics.py:17`). Report decision accuracy and a "safe decision" rate (rank(pred) ≥ rank(gold), minus wrong blocks) side by side, so the T5 BLOCK-instead-of-ESCALATE cases (7 of 26 with oracle) are visible for what they are.

**F7. Collected datasets.** Keep the shortcut caveats as written in `shortcut_check.md` (word model 88.6 vs 91-93; 43 R-Judge near-copies; AgentRisk reply rule 85.6; ATBench error cue untestable). The 1 h perturbation test (add a harmless tool-error turn to SAFE collected records, count flips) is the only way to test the ATBench shortcut; do it after the final rerun if a slot is free.

**F8. Metrics code.** `unsafe_action_rate`, `check_precision/recall`, `correct_missing_fact_rate` (`metrics.py:58-124`) and the seed bootstrap (`bootstrap.py`) match `decisions.md` R10; invalid output counts as wrong everywhere (conservative, R9.6). One gap: `check_recall` counts a record as "checked" when any call was made, so a two-check record with one call counts as recall 1.0; `check_results.md` adds "every needed check" for that reason. Use the latter in the report for T5.

## 4. Ideas considered and rejected

| Idea | Why not |
|---|---|
| More query engineering (resource kind, team, last-turn weighting) | Measured: the current all-turns query is the best of three forms; w is flat 0.5-0.6; 44 of 122 T1 gold policies are beyond rank 10 because the deciding fact is hidden by design, which no query fixes. |
| Learned dense retriever on train pairs | Policies are split-disjoint; 292 train queries; would memorise train policy wording. |
| Hyperparameter sweeps (rank, lr, epochs) | One run per configuration, no variance estimate, 6.5 h each, val too small to rank similar adapters. |
| Training on the retrieval condition | Target undefined when the deciding policy is missing; teaches guessing. |
| Fallback to ASK_CONFIRMATION when retrieval looks weak | Rank 1 still counts as "let through" against a BLOCK or ESCALATE gold; raises extra confirmations; no reliable miss detector. |
| Self-consistency / sampling | 5x inference cost; strictest-of-k trades unsafe for wrong blocks. |
| Switching back to the 30 Oct adapter | Would be choosing a model on test results; its val and collected-val numbers are within noise of the final one. |
| Changing the 5-point margin or the hypothesis after the results | Pre-registered in R10.4; changing it now is tuning on test. Report power instead (F2). |
| Qwen3-235B comparison | No endpoint decision by 5 Nov; a second prompt-only model does not address the checking problem. |
| Dropping the collected data from training | No evidence it hurts (collected val F1 stable, our val within noise); 6.5 h to find out. |
| Dropping Param's distractor turns or phase-2 records | Effects cannot be measured on val/test; removing them is as blind as adding them was. |
| Another retrain before 14 Nov | No way to tell improvement from run noise with one run; val cannot judge T5 changes; no time to recover from a worse adapter. |

## 5. Evidence quality

- Val has 40 records (16 seeds), 2 of them two-check; test 146 (62 seeds), OOD 112 (45 seeds). Accuracy intervals are ±10 to ±15 points; the Δ unsafe intervals are 26-30 points wide. Any single-run difference under about 8 points is noise.
- All adapter comparisons rest on one training run each (F4).
- The retrieval numbers in section 2 are exact for train+val; the downstream estimates (A1, E1) are my judgment from the correct-policies ceiling and the oracle results, not measurements.
- Items marked "motivated by test evidence" (E1, E3, B2) were found in the locked test reports; their train-side facts (one mechanism in train, the loop's one-ask rule) are verifiable without test, and the validation plans use val and train only.

## 6. Why val cannot settle the main question

The hypothesis fails on test because of two-check T5 records and retrieval. Val has 2 T5 records (IND-PRIV-T5-004 v1/v2), both two-check on `recipient_class` with the tool pair `check_user_authorization` + `check_recipient_type`, the same pair as 22 of the 26 train two-check records but a different fact: in `configs/fact_checks.yaml:276-280` `recipient_class` has one tool, so the second gold check comes from the policy's composite logic, not from a second source of one fact. E1's completion rule therefore never fires on val, and 15 of 40 val records have their gold policy in the retrieved top 3 (`decisions.md`, 2026-10-28 row). So val can confirm that a retrieval change finds more policies and that a loop or prompt change does no harm on one-check records, and it gives exactly 2 records of two-check behaviour. It cannot show that two-check behaviour improved. Say this in the report; for the next iteration keep a train-side dev set with every mechanism (F5).

The same fact matters for E1's reach: of the two kinds of two-check record, "one fact, two tools" (`account_type`, `modifiable`, `role_eligible`) is handled by the rule, and "one policy, two facts" (composite policies such as the val `recipient_class` case) only by the prompt line and by training data (B2, D1). I could not count how many test two-check records fall in each kind without reading test records; Param's 6 Nov note lists six mechanisms, of which `modifiable` and `role_eligible` are multi-tool facts.

## 7. Cross-encoder trial (A3)

`BAAI/bge-reranker-base` (cross-encoder, max length 512) re-ranked the current retriever's top 20 for each of the 332 train + val records, query = the evaluation query, plain and after the action filter. CPU, 1,093 s.

| | k=3 all gold shown | T1 | T2 | T3 | T4 | T5 | k=5 all | T1 | T2 | T3 | T4 | T5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hybrid retriever (section 2, for comparison) | **0.52** | 0.44 | 0.56 | 0.80 | 0.79 | 0.38 | **0.59** | 0.46 | 0.66 | 0.95 | 0.86 | 0.48 |
| re-ranked top 20, plain | 0.32 | 0.31 | 0.33 | 0.65 | 0.21 | 0.22 | 0.43 | 0.41 | 0.49 | 0.75 | 0.21 | 0.32 |
| action filter alone (section 2) | **0.63** | 0.61 | 0.61 | 0.95 | 0.86 | 0.48 | **0.74** | 0.69 | 0.76 | 1.00 | 0.86 | 0.68 |
| re-ranked top 20, after the filter | 0.44 | 0.48 | 0.38 | 0.90 | 0.39 | 0.30 | 0.61 | 0.66 | 0.57 | 1.00 | 0.68 | 0.42 |

**Rejected.** The re-ranker is 20 points worse than the hybrid retriever it re-ranks, in every case type. The policy lines are one short sentence (about 65 characters) and the query is a whole conversation; a general passage re-ranker scores that pair badly, and it has no notion of hidden facts either. A re-ranker fine-tuned on train pairs would face the split-disjoint policy problem of A5. Do not spend more time on re-ranking; the action tags (A1) are the retrieval change.
