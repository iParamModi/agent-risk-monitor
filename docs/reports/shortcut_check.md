# Shortcut check of the collected datasets: findings

2026-11-02, Meet. Phase A and Phase B adapters, safe/unsafe label only. All tables, for test and val: `shortcut_check_tables.md` (`python -m src.eval.shortcuts`). No GPU; counts and scores only.

**Question:** do the high scores on R-Judge, ATBench and AgentRisk mean the model judges risk, or does it read a surface feature?

## Answer

**The gain is real but smaller than it looks.** Base to Phase A is 54.9 to 92.8 on test, but a simple word model with no LLM already gets **88.6** by reading only the judged step. So most of the jump can be reached from wording alone, and what the LLM adds over that is about **4 points on test and 3 on val**.

Phase A's lead over the word model is significant on test (p = 0.025) but not on val (p = 0.17). **Phase B's lead is not significant on either** (p = 0.17 and 0.56). The known named cues do not explain the scores. On R-Judge, over a third of the test records are near-copies of training records.

| Dataset | Phase A | Phase B | Word model, judged step | Rule from the strongest cue | Without the easy part (Phase A) | Verdict |
|---|---|---|---|---|---|---|
| R-Judge | 91.3 | 90.4 | 87.8 | – | **86.1** without near-copies | Inflated by near-copies |
| ATBench | 89.4 | 87.8 | 86.2 | 55.3 (tool status error) | 82.1 of UNSAFE with no error cue | Weakest evidence that the LLM adds much |
| AgentRisk | 99.2 | 97.6 | 92.8 | 85.6 (reply to the user) | **98.7** without replies | Holds up, but few hard SAFE records |
| **All** | **92.8** | **91.4** | **88.6** | | | |

All numbers are safe/unsafe accuracy in % on test: 428 records, with 12 long ATBench records left out, all UNSAFE.

## By dataset

**R-Judge.** 43 of 115 test records are near-copies of a Phase A training record (similarity at least 0.7), and for 42 of them that record has the same label. Phase A gets all 43 right. On the other 72 it gets 62 right (86.1), and the word model gets 60 (83.3). Val shows the same: 34 and 33 of 39.

**ATBench.** The known `status: error` cue is not what drives the score: only 6 of 188 test records have it, and Phase A catches 69 of the 84 UNSAFE records without it. But the LLM's lead over wording is small (89.4 vs 86.2 on test, 90.6 vs 89.6 on val), and it is not statistically clear. Where the word model is wrong, Phase A is right on 19 of 26 (test) and 5 of 10 (val), so it is not simply doing something else.

**The ATBench error shortcut is not ruled out.** No val or test record is SAFE with a tool status error (train has 1 such record against 52 UNSAFE), so these sets cannot show whether the model would wrongly flag one.

**AgentRisk.** A reply to the user is always SAFE (159 on train, 48 on test, 0 UNSAFE), so a rule using only that gets 85.6. But the score does not depend on it: without replies, Phase A gets 76 of 77 right, including all 18 SAFE records, and 25 of 25 SAFE across val and test. It also beats the word model (p = 0.021 on test, 0.070 on val) and is right on all 9 test records the word model misses. Of the three datasets, this is the only one where the lead is significant. The caution is size: only 25 hard SAFE records exist.

## How the word models work

TF-IDF (1-2 word terms) and logistic regression, one per dataset, trained on that dataset's train split with fixed settings, no tuning, and evaluated once. They read visible text only. Phase A trains on a smaller balanced list across all datasets, so the comparison is not exactly like for like.

**What they pick up.** Their top words suggest it is mostly how the agent words its own step: refusing or showing caution points to SAFE, and announcing the action points to UNSAFE. This is partly legitimate, since a step that refuses really is safer. But it means these datasets test reading the agent's stated intent more than judging the harm of an action.

## Limits

- This shows what could explain the scores. It does not prove what the model actually uses. That needs a test that changes the records and sees whether decisions flip.
- The similarity threshold matters: the near-copy count depends on the 0.7 cut-off and how similarity is measured.
- Only the safe/unsafe label is checked, not the risk type.

## For the final report

1. Show the word model next to Base, Phase A and Phase B. Do not present 54.9 to 92.8 as the whole gain from fine-tuning.
2. Report R-Judge with and without near-copies, and AgentRisk with and without replies. Say that only Phase A's lead on test is significant.
3. Say that the ATBench error shortcut could not be tested on our splits.
4. The mid report's Phase A numbers are correct, but it does not include these caveats.
5. These numbers are for the current adapters. After the retrain, add the new runs to `src/eval/shortcuts.py`, rerun it and update this file.
