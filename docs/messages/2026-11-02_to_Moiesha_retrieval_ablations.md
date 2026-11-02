# To Moiesha: retrieval and ablations for the final submission (from Meet, 2026-11-02)

Final submission is **14 Nov**. Retrieval must be frozen by **8 Nov**, because I retrain once on 8-9 Nov and the training file also uses the retriever.

Start with `docs/reports/error_analysis_val.md`. It shows where the monitor goes wrong on validation.

## Your tasks, most important first

| # | Task | By | Done when |
|---|---|---|---|
| 1 | Better policy retrieval | 7 Nov | Recall@3 improved on train + val, and new values frozen in the code |
| 2 | Ablation code | 8 Nov | The 3 options below work in a dry run (no GPU), with tests |
| 3 | Decide on Qwen3-235B | 5 Nov | You tell us: a free hosted endpoint exists, or we drop it |
| 4 | Ablation tables | 12 Nov | `outputs/tables/ablations.md` from the runs |
| 5 | Agreement study (κ) on our records, with Param | 11 Nov | Your labels are done (Param organises) |
| 6 | Final report: related work | 12 Nov | PLAN Step 25, items 1-3, 5 and 6 |

## 1. Retrieval: this is our biggest problem

On val, Phase B with selective checking gets 11 of 40 wrong. **In 9 of those 11 the deciding policy was not among the 3 shown**, so the monitor could not have known the rule. When it is shown the correct policies, it gets only 6 of 40 wrong.

Today: BM25 + `bge-base-en-v1.5`, w = 0.6, top 3, with recall@3 = 0.55 on train + val (see `src/policies/retriever.py`).

Try these, one at a time, and keep what helps:
1. Filter or boost policies by the proposed action's tool.
2. A different weight per action.
3. A cross-encoder re-ranker on the top 20.
4. Showing more than 3 policies. This also lengthens the prompt, so tell me before choosing it.

Measure the share of records where **all** deciding policies are shown, not just one. A T5 policy conflict needs both sides of the conflict in the list, or the monitor cannot see the conflict. Report recall per case type.

`scripts/eval_retrieval.py` works on seeds and its header is out of date. The 0.55 was measured on records, with `query_for(visible, all_turns=True)`, so please extend the script to do that.

## 2. Ablation code

All of these go through `src/monitor/case_inputs.py` and `src/monitor/run.py`:

| Ablation | What to add |
|---|---|
| **A2, no policies** | A `"none"` value in `POLICY_MODES`: the prompt shows no policies |
| **A6, noisy checks** | Pass `NoiseConfig(rate=0.1, seed=...)` to `for_record(...)`. The gateway already supports it (`src/gateway/noise.py`) but monitor runs do not use it yet. Noise is for evaluation only |
| **Top-k** | Make `N_SHOWN` a setting: k = 1, 3, 5 |

Test with `--dry-run`, which needs no GPU. When it is in `main`, tell me and **I will run the Kaggle jobs**, since the adapter is private in my account.

## 3. Qwen3-235B

The proposal promised it, and the mid report lists a "larger model" ablation. It is too big for Kaggle's GPUs, so it needs a hosted API. `OpenAICompatModel` in `src/monitor/models.py` is ready for an endpoint. Please check for a free option. If there is none, we drop it and say so in the report.

## ⚠️ Be careful

- **Tune on train and val only. Never on test or OOD.** Do not open `error_analysis_test.md`, `error_notes_test.md` or any OOD report while choosing retrieval settings.
- **Val is small (40 records).** Do not trust a gain of 1 or 2 records. Use train + val for retrieval, as we did for w = 0.6.
- Only the visible policy text may be indexed. Do not use `policy_logic.yaml` (R8.1).
- The agreement study is **humans only, no LLM** (CLAUDE.md §6).
