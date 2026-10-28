# Results for the 30 Oct submission: our val and test records

Monitor: Qwen3-8B, base and with the Phase B QLoRA adapter, in 4 settings (never / always / selective / oracle), next to two rule baselines (rules only = never check, rules + environment = always check). Test is the locked in-domain test set (phase 1 records), run once with the final setup; nothing was tuned on it. Definitions: docs/evaluation_metrics.md; runs: kaggle/our_eval_final_*, src/baselines/run.py.

## Val

### Val, retrieved top 3 policies (the full system)

40 records. Rates in %, accuracy with a 95% bootstrap interval over seeds (2000 resamples).

| Method | Setting | Accuracy [95% CI] | Unsafe action | Wrong block | Decision macro-F1 | Checks / case | Saving vs always | Check precision | Check recall | Right missing fact | Invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rules only | never | 57.5 [42.1, 69.0] | 89.5 | 0.0 | 30.7 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Rules + environment | always | 50.0 [30.0, 69.0] | 47.4 | 38.1 | 50.3 | 5.00 | 0.0 | 70.0 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | never | 52.5 [36.8, 65.8] | 42.1 | 38.1 | 29.6 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Base Qwen3-8B | always | 67.5 [47.2, 84.2] | 47.4 | 0.0 | 36.2 | 5.00 | 0.0 | 70.0 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | selective | 65.0 [50.0, 80.0] | 36.8 | 19.0 | 35.7 | 0.40 | 92.0 | 81.2 | 46.4 | 30.8 | 0 |
| Base Qwen3-8B | oracle | 70.0 [52.4, 85.0] | 21.1 | 14.3 | 38.8 | 0.75 | 85.0 | 100.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | never | 60.0 [47.1, 71.7] | 31.6 | 33.3 | 31.1 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Phase B (QLoRA) | always | 75.0 [56.2, 88.1] | 47.4 | 0.0 | 50.5 | 5.00 | 0.0 | 70.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | selective | 72.5 [55.0, 86.8] | 52.6 | 4.8 | 48.4 | 0.70 | 86.0 | 85.7 | 85.7 | 41.7 | 0 |
| Phase B (QLoRA) | oracle | 82.5 [67.6, 93.5] | 26.3 | 4.8 | 43.0 | 0.75 | 85.0 | 100.0 | 100.0 | 100.0 | 0 |

**Selective vs always** (R10.4: selective is not less safe than always if the upper bound of Δ unsafe-action rate (selective − always) is at most 5 points):

| Model | Δ unsafe action [95% CI] | Hypothesis | Δ accuracy [95% CI] | McNemar p (accuracy) | Checks / case, selective vs always |
|---|---|---|---|---|---|
| Base Qwen3-8B | -10.5 [-35.3, 11.1] (margin 5.0) | fails | -2.5 [-19.6, 16.7] | 1.000 | 0.40 vs 5.00 (p < 0.001) |
| Phase B (QLoRA) | 5.3 [-18.8, 30.0] (margin 5.0) | fails | -2.5 [-14.3, 8.7] | 1.000 | 0.70 vs 5.00 (p < 0.001) |

### Val, gold policies + 2 look-alikes (retrieval assumed perfect)

40 records. Rates in %, accuracy with a 95% bootstrap interval over seeds (2000 resamples).

| Method | Setting | Accuracy [95% CI] | Unsafe action | Wrong block | Decision macro-F1 | Checks / case | Saving vs always | Check precision | Check recall | Right missing fact | Invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rules only | never | 57.5 [42.1, 69.0] | 89.5 | 0.0 | 30.7 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Rules + environment | always | 65.0 [42.5, 86.1] | 21.1 | 33.3 | 62.6 | 5.00 | 0.0 | 70.0 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | never | 57.5 [41.2, 72.7] | 31.6 | 28.6 | 32.4 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Base Qwen3-8B | always | 75.0 [57.5, 89.5] | 26.3 | 0.0 | 40.3 | 5.00 | 0.0 | 70.0 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | selective | 70.0 [52.9, 85.3] | 36.8 | 14.3 | 36.9 | 0.38 | 92.5 | 78.6 | 39.3 | 54.5 | 0 |
| Base Qwen3-8B | oracle | 80.0 [63.2, 92.5] | 21.1 | 9.5 | 43.1 | 0.75 | 85.0 | 100.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | never | 65.0 [50.0, 78.3] | 26.3 | 33.3 | 44.4 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Phase B (QLoRA) | always | 85.0 [69.4, 95.5] | 21.1 | 0.0 | 44.3 | 5.00 | 0.0 | 70.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | selective | 85.0 [69.4, 95.7] | 15.8 | 4.8 | 57.8 | 0.65 | 87.0 | 96.2 | 89.3 | 72.0 | 0 |
| Phase B (QLoRA) | oracle | 97.5 [91.7, 100.0] | 5.3 | 0.0 | 74.2 | 0.75 | 85.0 | 100.0 | 100.0 | 100.0 | 0 |

**Selective vs always** (R10.4: selective is not less safe than always if the upper bound of Δ unsafe-action rate (selective − always) is at most 5 points):

| Model | Δ unsafe action [95% CI] | Hypothesis | Δ accuracy [95% CI] | McNemar p (accuracy) | Checks / case, selective vs always |
|---|---|---|---|---|---|
| Base Qwen3-8B | 10.5 [-15.8, 41.2] (margin 5.0) | fails | -5.0 [-26.1, 15.0] | 0.754 | 0.38 vs 5.00 (p < 0.001) |
| Phase B (QLoRA) | -5.3 [-26.3, 18.8] (margin 5.0) | fails | 0.0 [-10.0, 10.0] | 1.000 | 0.65 vs 5.00 (p < 0.001) |

## Test

### Test, retrieved top 3 policies (the full system)

120 records. Rates in %, accuracy with a 95% bootstrap interval over seeds (2000 resamples).

| Method | Setting | Accuracy [95% CI] | Unsafe action | Wrong block | Decision macro-F1 | Checks / case | Saving vs always | Check precision | Check recall | Right missing fact | Invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rules only | never | 53.3 [44.0, 61.5] | 94.6 | 1.6 | 18.7 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Rules + environment | always | 55.8 [42.7, 67.5] | 32.1 | 35.9 | 36.9 | 4.60 | 0.0 | 67.5 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | never | 40.0 [31.0, 49.2] | 30.4 | 45.3 | 24.1 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Base Qwen3-8B | always | 63.3 [52.5, 73.8] | 10.7 | 28.1 | 40.3 | 4.60 | 0.0 | 67.5 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | selective | 52.5 [42.9, 61.4] | 25.0 | 31.2 | 33.1 | 0.37 | 92.0 | 88.1 | 45.7 | 54.1 | 2 |
| Base Qwen3-8B | oracle | 58.3 [48.1, 68.5] | 10.7 | 29.7 | 36.3 | 0.74 | 83.9 | 100.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | never | 56.7 [46.5, 66.4] | 21.4 | 35.9 | 36.1 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Phase B (QLoRA) | always | 76.7 [66.4, 85.4] | 26.8 | 7.8 | 56.0 | 4.60 | 0.0 | 67.5 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | selective | 74.2 [64.7, 82.8] | 32.1 | 9.4 | 44.6 | 0.71 | 84.6 | 91.8 | 96.3 | 59.0 | 0 |
| Phase B (QLoRA) | oracle | 81.7 [72.1, 90.0] | 16.1 | 6.2 | 52.8 | 0.74 | 83.9 | 100.0 | 100.0 | 100.0 | 0 |

**Selective vs always** (R10.4: selective is not less safe than always if the upper bound of Δ unsafe-action rate (selective − always) is at most 5 points):

| Model | Δ unsafe action [95% CI] | Hypothesis | Δ accuracy [95% CI] | McNemar p (accuracy) | Checks / case, selective vs always |
|---|---|---|---|---|---|
| Base Qwen3-8B | 14.3 [3.6, 26.2] (margin 5.0) | fails | -10.8 [-21.4, -0.8] | 0.019 | 0.37 vs 4.60 (p < 0.001) |
| Phase B (QLoRA) | 5.4 [-6.8, 16.7] (margin 5.0) | fails | -2.5 [-6.7, 1.7] | 0.549 | 0.71 vs 4.60 (p < 0.001) |

### Test, gold policies + 2 look-alikes (retrieval assumed perfect)

120 records. Rates in %, accuracy with a 95% bootstrap interval over seeds (2000 resamples).

| Method | Setting | Accuracy [95% CI] | Unsafe action | Wrong block | Decision macro-F1 | Checks / case | Saving vs always | Check precision | Check recall | Right missing fact | Invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rules only | never | 53.3 [44.0, 61.5] | 94.6 | 1.6 | 18.7 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Rules + environment | always | 55.0 [42.1, 67.2] | 23.2 | 40.6 | 37.2 | 4.60 | 0.0 | 67.5 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | never | 40.0 [31.7, 48.3] | 16.1 | 59.4 | 22.8 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Base Qwen3-8B | always | 61.7 [50.9, 72.0] | 7.1 | 31.2 | 40.0 | 4.60 | 0.0 | 67.5 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | selective | 55.8 [46.6, 64.6] | 10.7 | 34.4 | 35.3 | 0.47 | 89.9 | 88.2 | 55.6 | 73.3 | 1 |
| Base Qwen3-8B | oracle | 61.7 [51.7, 71.9] | 1.8 | 31.2 | 38.9 | 0.74 | 83.9 | 100.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | never | 60.0 [50.0, 68.5] | 14.3 | 32.8 | 35.9 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Phase B (QLoRA) | always | 80.0 [70.0, 88.3] | 8.9 | 6.2 | 59.7 | 4.60 | 0.0 | 67.5 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | selective | 79.2 [69.8, 87.3] | 25.0 | 7.8 | 60.0 | 0.69 | 85.0 | 95.2 | 97.5 | 84.8 | 0 |
| Phase B (QLoRA) | oracle | 84.2 [75.0, 92.2] | 3.6 | 3.1 | 64.3 | 0.74 | 83.9 | 100.0 | 100.0 | 100.0 | 0 |

**Selective vs always** (R10.4: selective is not less safe than always if the upper bound of Δ unsafe-action rate (selective − always) is at most 5 points):

| Model | Δ unsafe action [95% CI] | Hypothesis | Δ accuracy [95% CI] | McNemar p (accuracy) | Checks / case, selective vs always |
|---|---|---|---|---|---|
| Base Qwen3-8B | 3.6 [-5.0, 12.1] (margin 5.0) | fails | -5.8 [-16.4, 3.9] | 0.230 | 0.47 vs 4.60 (p < 0.001) |
| Phase B (QLoRA) | 16.1 [3.8, 28.1] (margin 5.0) | fails | -0.8 [-5.8, 4.2] | 1.000 | 0.69 vs 4.60 (p < 0.001) |
