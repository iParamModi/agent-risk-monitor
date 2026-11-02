# To Param: data work for the final submission (from Meet, 2026-11-02)

Final submission is **14 Nov**. All training data must be in `main` by **8 Nov**, because I retrain once on 8-9 Nov (about 6 h on Kaggle) and there is no time for a second retrain.

Start with `docs/reports/error_analysis_val.md`. It shows where the monitor goes wrong on validation.

## Your tasks, most important first

| # | Task | By | Done when |
|---|---|---|---|
| 1 | More T5 "facts disagree" seeds, train only | 5 Nov | At least 8 new seeds across domains; `make records`: 0 problems |
| 2 | Check 1 val record: IND-ACC-T1-001 | 5 Nov | You say whether the label is right, or fix the seed |
| 3 | Distractor turns in train records | 6 Nov | About 30% of train pairs have one; Changelog row added |
| 4 | Phase-2 tools, seeds and records | 8 Nov | Tools in the company and gateway, seeds and records made, tests pass |
| 5 | Agreement study (κ) on our records, with Moiesha | 11 Nov | `docs/labeling_guide.md`, labels and `kappa_report.json` in the repo |

If time runs short, **cut task 4 first** and tell me by 7 Nov, so the report can say so.

## 1. T5 seeds

When a T5 "facts disagree" case needs two checks, Phase B often makes only one, even when it is shown the correct policies. On val, IND-PRIV-T5-004 asks only for `check_user_authorization`, gets one fact, and says BLOCK instead of ESCALATE.

The training file does ask for both checks, so this is not a bug. There are just very few examples: only **10 train records (5 seeds)** need two checks, out of 496 first-pass examples.

- Add new seeds with `key_fact` pairs that disagree, in the same format as the existing T5 seeds, with `required_checks` filled.
- Cover the domains that have few T5 seeds (FIN, PRIV, REPO and CAL have the fewest).
- Pin the new seeds to **train** in `splits.yaml`, as you did for the 5 train-only seeds on 28 Oct.

## 2. IND-ACC-T1-001 (val)

The check Phase B makes, `check_user_authorization`, returns `access_level = none`, so it says BLOCK. The label says ALLOW, because the policy only looks at `authorized_financial` from `check_user_clearance`.

A user with no access being allowed could be a real label problem and not a model mistake. Please read the seed and decide. If you change it, follow the normal seed route: never edit a label by hand.

## 3. Distractor turns

ATBench has a shortcut: `"status": "error"` turns are 108 UNSAFE and 1 SAFE, so the model can learn "error means unsafe". The mid report says we plan to fix this.

Agreed fix:
- Add one distractor tool turn (a tool error or injected text) to about 30% of train pairs.
- It must be identical on sides A and B and about a different resource than `key_fact`. The agent never follows the injection.
- Keep the templates in `configs/distractors.yaml`.
- Add a Changelog row in `docs/decisions.md`, since this was never written down.

**Train records only.** Val, test and OOD do not change.

## 4. Phase 2

Today phase 2 has only the 4 `create_event` seeds. The tool list is in `configs/tool_phases.yaml` (`phase2`):
- Write seeds for those tools and add the tools to `lma_agent`. Ask Prateek to review the `lma_agent` changes, since he owns it.
- Add rows to `configs/check_table.yaml` and make sure `scripts/check_table_errors.py` shows 0 failures.

## 5. Agreement study

So far we only have κ = 0.57 on R-Judge, below the 0.6 target. PLAN Step 10 asks for more:
- Write `docs/labeling_guide.md`.
- Pick 60 of our records and 40 collected ones.
- Moiesha and you label separately, without seeing each other's answers or the labels. Label records you did not write, where you can.

**Humans only, no LLM (CLAUDE.md §6).**

## ⚠️ Be careful

- **Do not look at `docs/reports/error_analysis_test.md`, `error_notes_test.md` or any OOD report when choosing what to add.** Only val may guide changes. Otherwise the final test number is not honest.
- **The 120 phase-1 test records and the 112 OOD records must stay byte-identical.** Run `python scripts/changed_records.py` before any `--relock` and send me the output.
- New phase-2 test seeds change `test.jsonl`, so they need `--relock` and a Changelog row. Only additions may appear in the list.
- Keep the rule that no policy appears in two splits.
