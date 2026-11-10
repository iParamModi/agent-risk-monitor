# To Moiesha: retrieval cutoff for the final runs (from Meet, 2026-11-10)

Retrieval and the ablation code were due on 7 and 8 Nov, and nothing has been pushed yet. I started the final Phase B retrain today (Kaggle, about 6.5 h) with the **current** retriever (BM25 + `bge-base-en-v1.5`, w = 0.6, top 3, recall@3 0.55). Training only uses it to pick the 2 look-alike policies, so a new retriever can still be used in the final runs.

## Cutoff: 11 Nov, 10:00

| What | If pushed by 11 Nov 10:00 | If not |
|---|---|---|
| Better retrieval (frozen values in `src/policies/retriever.py`, tests pass, recall@3 on train + val) | The final runs use it | The final runs use the current retriever, and the report says retrieval was not improved |
| Ablation code (no policies, noise, top-k; dry run with tests) | I run the ablation jobs on 11-12 Nov | Ablations are cut to what the code already supports, or dropped |
| Qwen3-235B decision | – | Dropped |

Push to `main` and add a line to the Activity Log in `PROGRESS.md`, so I see it. Tune only on train + val, never on test or OOD.

Still yours after that: κ labels (11 Nov, with Param), ablation tables (12 Nov), related work for the report (12 Nov).
