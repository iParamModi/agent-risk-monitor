# Results: Val, Test, OOD records

Monitor: Qwen3-8B, base and with the Phase B QLoRA adapter, in 4 settings (never / always / selective / oracle), next to two rule baselines (rules only = never check, rules + environment = always check). Test is the locked in-domain test set (phase 1 records), OOD the locked out-of-domain test set; nothing was tuned on them. Definitions: docs/evaluation_metrics.md; runs: kaggle/our_eval_final_*, src/baselines/run.py.

## Val

### Val, retrieved top 3 policies (the full system)

40 records. Rates in %, accuracy with a 95% bootstrap interval over seeds (2000 resamples).

| Method | Setting | Accuracy [95% CI] | Unsafe action | Wrong block | Decision macro-F1 | Checks / case | Saving vs always | Check precision | Check recall | Right missing fact | Invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rules only | never | 57.5 [42.1, 69.0] | 89.5 | 0.0 | 30.7 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Rules + environment | always | 50.0 [30.0, 69.0] | 47.4 | 38.1 | 50.3 | 5.00 | 0.0 | 70.0 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | never | 52.5 [36.8, 65.8] | 42.1 | 38.1 | 29.6 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Base Qwen3-8B | always | 67.5 [47.2, 84.2] | 47.4 | 0.0 | 36.2 | 5.00 | 0.0 | 70.0 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | selective | 57.5 [42.5, 71.4] | 42.1 | 23.8 | 32.1 | 0.23 | 95.5 | 66.7 | 21.4 | 16.7 | 0 |
| Base Qwen3-8B | oracle | 70.0 [52.4, 85.0] | 21.1 | 14.3 | 38.8 | 0.75 | 85.0 | 100.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | never | 67.5 [44.4, 84.8] | 52.6 | 4.8 | 34.2 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Phase B (QLoRA) | always | 70.0 [50.0, 85.0] | 42.1 | 0.0 | 35.2 | 5.00 | 0.0 | 70.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | selective | 67.5 [52.8, 80.4] | 52.6 | 9.5 | 44.4 | 0.68 | 86.5 | 88.0 | 78.6 | 45.5 | 0 |
| Phase B (QLoRA) | oracle | 90.0 [76.3, 100.0] | 21.1 | 0.0 | 92.7 | 0.75 | 85.0 | 100.0 | 100.0 | 100.0 | 0 |

**Selective vs always** (R10.4: selective is not less safe than always if the upper bound of Δ unsafe-action rate (selective − always) is at most 5 points):

| Model | Δ unsafe action [95% CI] | Hypothesis | Δ accuracy [95% CI] | McNemar p (accuracy) | Checks / case, selective vs always |
|---|---|---|---|---|---|
| Base Qwen3-8B | -5.3 [-31.9, 21.1] (margin 5.0) | fails | -10.0 [-26.1, 8.3] | 0.344 | 0.23 vs 5.00 (p < 0.001) |
| Phase B (QLoRA) | 10.5 [-18.2, 41.2] (margin 5.0) | fails | -2.5 [-16.7, 12.5] | 1.000 | 0.68 vs 5.00 (p < 0.001) |

### Val, gold policies + 2 look-alikes (retrieval assumed perfect)

40 records. Rates in %, accuracy with a 95% bootstrap interval over seeds (2000 resamples).

| Method | Setting | Accuracy [95% CI] | Unsafe action | Wrong block | Decision macro-F1 | Checks / case | Saving vs always | Check precision | Check recall | Right missing fact | Invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rules only | never | 57.5 [42.1, 69.0] | 89.5 | 0.0 | 30.7 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Rules + environment | always | 65.0 [42.5, 86.1] | 21.1 | 33.3 | 62.6 | 5.00 | 0.0 | 70.0 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | never | 57.5 [41.2, 72.7] | 31.6 | 28.6 | 32.4 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Base Qwen3-8B | always | 75.0 [57.5, 89.5] | 26.3 | 0.0 | 40.3 | 5.00 | 0.0 | 70.0 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | selective | 70.0 [52.6, 85.7] | 31.6 | 19.0 | 37.0 | 0.28 | 94.5 | 72.7 | 28.6 | 50.0 | 0 |
| Base Qwen3-8B | oracle | 80.0 [63.2, 92.5] | 21.1 | 9.5 | 43.1 | 0.75 | 85.0 | 100.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | never | 75.0 [55.6, 89.1] | 47.4 | 4.8 | 39.1 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Phase B (QLoRA) | always | 82.5 [65.8, 93.5] | 26.3 | 0.0 | 42.2 | 5.00 | 0.0 | 70.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | selective | 82.5 [71.1, 92.9] | 26.3 | 9.5 | 87.3 | 0.70 | 86.0 | 95.8 | 82.1 | 73.9 | 0 |
| Phase B (QLoRA) | oracle | 97.5 [91.7, 100.0] | 5.3 | 0.0 | 74.2 | 0.75 | 85.0 | 100.0 | 100.0 | 100.0 | 0 |

**Selective vs always** (R10.4: selective is not less safe than always if the upper bound of Δ unsafe-action rate (selective − always) is at most 5 points):

| Model | Δ unsafe action [95% CI] | Hypothesis | Δ accuracy [95% CI] | McNemar p (accuracy) | Checks / case, selective vs always |
|---|---|---|---|---|---|
| Base Qwen3-8B | 5.3 [-23.8, 36.9] (margin 5.0) | fails | -5.0 [-26.2, 17.5] | 0.774 | 0.28 vs 5.00 (p < 0.001) |
| Phase B (QLoRA) | 0.0 [-21.1, 21.1] (margin 5.0) | fails | 0.0 [-12.5, 16.7] | 1.000 | 0.70 vs 5.00 (p < 0.001) |

## Test

### Test, retrieved top 3 policies (the full system)

146 records. Rates in %, accuracy with a 95% bootstrap interval over seeds (2000 resamples).

| Method | Setting | Accuracy [95% CI] | Unsafe action | Wrong block | Decision macro-F1 | Checks / case | Saving vs always | Check precision | Check recall | Right missing fact | Invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rules only | never | 43.8 [34.3, 52.5] | 93.9 | 1.6 | 16.6 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Rules + environment | always | 52.7 [40.5, 63.7] | 39.0 | 35.9 | 38.5 | 4.82 | 0.0 | 73.3 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | never | 35.6 [27.1, 43.7] | 28.0 | 50.0 | 24.5 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Base Qwen3-8B | always | 52.7 [42.6, 62.7] | 17.1 | 26.6 | 41.2 | 4.82 | 0.0 | 73.3 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | selective | 39.0 [30.9, 47.2] | 29.3 | 35.9 | 24.7 | 0.38 | 92.2 | 90.6 | 44.9 | 50.0 | 2 |
| Base Qwen3-8B | oracle | 48.6 [38.4, 58.2] | 14.6 | 31.2 | 35.5 | 0.97 | 80.0 | 100.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | never | 58.2 [47.1, 68.4] | 29.3 | 15.6 | 43.7 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Phase B (QLoRA) | always | 65.8 [55.1, 75.3] | 34.1 | 4.7 | 52.3 | 4.82 | 0.0 | 73.3 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | selective | 61.6 [50.7, 72.0] | 52.4 | 7.8 | 40.4 | 0.72 | 85.1 | 97.0 | 89.7 | 46.9 | 0 |
| Phase B (QLoRA) | oracle | 76.0 [66.2, 84.0] | 20.7 | 1.6 | 55.4 | 0.97 | 80.0 | 100.0 | 100.0 | 100.0 | 0 |

**Selective vs always** (R10.4: selective is not less safe than always if the upper bound of Δ unsafe-action rate (selective − always) is at most 5 points):

| Model | Δ unsafe action [95% CI] | Hypothesis | Δ accuracy [95% CI] | McNemar p (accuracy) | Checks / case, selective vs always |
|---|---|---|---|---|---|
| Base Qwen3-8B | 12.2 [1.2, 24.1] (margin 5.0) | fails | -13.7 [-21.5, -6.9] | < 0.001 | 0.38 vs 4.82 (p < 0.001) |
| Phase B (QLoRA) | 18.3 [8.2, 28.9] (margin 5.0) | fails | -4.1 [-10.6, 1.9] | 0.263 | 0.72 vs 4.82 (p < 0.001) |

### Test, gold policies + 2 look-alikes (retrieval assumed perfect)

146 records. Rates in %, accuracy with a 95% bootstrap interval over seeds (2000 resamples).

| Method | Setting | Accuracy [95% CI] | Unsafe action | Wrong block | Decision macro-F1 | Checks / case | Saving vs always | Check precision | Check recall | Right missing fact | Invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rules only | never | 43.8 [34.3, 52.5] | 95.1 | 1.6 | 16.6 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Rules + environment | always | 52.1 [39.9, 63.6] | 28.0 | 40.6 | 39.4 | 4.82 | 0.0 | 73.3 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | never | 34.2 [26.8, 41.4] | 23.2 | 59.4 | 23.5 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Base Qwen3-8B | always | 52.1 [41.8, 62.5] | 12.2 | 29.7 | 42.0 | 4.82 | 0.0 | 73.3 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | selective | 43.8 [34.7, 52.6] | 24.4 | 39.1 | 30.7 | 0.50 | 89.6 | 91.0 | 57.0 | 62.3 | 2 |
| Base Qwen3-8B | oracle | 51.4 [41.3, 60.6] | 6.1 | 31.2 | 39.4 | 0.97 | 80.0 | 100.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | never | 61.0 [49.3, 70.9] | 29.3 | 14.1 | 44.5 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Phase B (QLoRA) | always | 75.3 [65.4, 84.0] | 12.2 | 4.7 | 63.5 | 4.82 | 0.0 | 73.3 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | selective | 69.2 [58.2, 78.7] | 41.5 | 4.7 | 48.3 | 0.71 | 85.4 | 96.9 | 88.8 | 80.0 | 0 |
| Phase B (QLoRA) | oracle | 86.3 [79.2, 92.3] | 3.7 | 1.6 | 64.3 | 0.97 | 80.0 | 100.0 | 100.0 | 100.0 | 0 |

**Selective vs always** (R10.4: selective is not less safe than always if the upper bound of Δ unsafe-action rate (selective − always) is at most 5 points):

| Model | Δ unsafe action [95% CI] | Hypothesis | Δ accuracy [95% CI] | McNemar p (accuracy) | Checks / case, selective vs always |
|---|---|---|---|---|---|
| Base Qwen3-8B | 12.2 [1.3, 23.0] (margin 5.0) | fails | -8.2 [-16.9, -0.7] | 0.029 | 0.50 vs 4.82 (p < 0.001) |
| Phase B (QLoRA) | 29.3 [16.7, 42.2] (margin 5.0) | fails | -6.2 [-15.8, 2.8] | 0.150 | 0.71 vs 4.82 (p < 0.001) |

## OOD

### OOD, retrieved top 3 policies (the full system)

112 records. Rates in %, accuracy with a 95% bootstrap interval over seeds (2000 resamples).

| Method | Setting | Accuracy [95% CI] | Unsafe action | Wrong block | Decision macro-F1 | Checks / case | Saving vs always | Check precision | Check recall | Right missing fact | Invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rules only | never | 54.5 [45.2, 62.7] | 100.0 | 0.0 | 17.6 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Rules + environment | always | 47.3 [35.8, 58.5] | 52.9 | 41.0 | 29.0 | 4.50 | 0.0 | 63.4 | 100.0 | 97.2 | 0 |
| Base Qwen3-8B | never | 43.8 [34.9, 52.7] | 25.5 | 59.0 | 29.0 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Base Qwen3-8B | always | 49.1 [39.8, 58.2] | 39.2 | 45.9 | 26.4 | 4.50 | 0.0 | 63.4 | 100.0 | 97.2 | 0 |
| Base Qwen3-8B | selective | 46.4 [37.0, 56.0] | 25.5 | 62.3 | 32.0 | 0.24 | 94.6 | 76.9 | 28.2 | 50.0 | 1 |
| Base Qwen3-8B | oracle | 55.4 [44.1, 66.4] | 17.6 | 45.9 | 34.6 | 0.65 | 85.5 | 100.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | never | 60.7 [49.1, 71.3] | 25.5 | 37.7 | 48.4 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Phase B (QLoRA) | always | 59.8 [50.0, 70.3] | 37.3 | 23.0 | 38.2 | 4.50 | 0.0 | 63.4 | 100.0 | 97.2 | 0 |
| Phase B (QLoRA) | selective | 67.0 [56.6, 76.6] | 37.3 | 21.3 | 48.7 | 0.76 | 83.1 | 83.5 | 93.0 | 59.1 | 0 |
| Phase B (QLoRA) | oracle | 75.9 [66.1, 84.2] | 21.6 | 16.4 | 52.2 | 0.65 | 85.5 | 100.0 | 100.0 | 100.0 | 0 |

**Selective vs always** (R10.4: selective is not less safe than always if the upper bound of Δ unsafe-action rate (selective − always) is at most 5 points):

| Model | Δ unsafe action [95% CI] | Hypothesis | Δ accuracy [95% CI] | McNemar p (accuracy) | Checks / case, selective vs always |
|---|---|---|---|---|---|
| Base Qwen3-8B | -13.7 [-28.8, 2.0] (margin 5.0) | **passes** | -2.7 [-14.2, 8.5] | 0.728 | 0.24 vs 4.50 (p < 0.001) |
| Phase B (QLoRA) | 0.0 [-13.2, 13.2] (margin 5.0) | fails | 7.1 [-4.8, 19.1] | 0.215 | 0.76 vs 4.50 (p < 0.001) |

### OOD next to in-domain test, retrieved top 3 policies (the full system)

| Model | Setting | Test accuracy | OOD accuracy | Test unsafe | OOD unsafe |
|---|---|---|---|---|---|
| Base Qwen3-8B | never | 35.6 | 43.8 | 28.0 | 25.5 |
| Base Qwen3-8B | always | 52.7 | 49.1 | 17.1 | 39.2 |
| Base Qwen3-8B | selective | 39.0 | 46.4 | 29.3 | 25.5 |
| Base Qwen3-8B | oracle | 48.6 | 55.4 | 14.6 | 17.6 |
| Phase B (QLoRA) | never | 58.2 | 60.7 | 29.3 | 25.5 |
| Phase B (QLoRA) | always | 65.8 | 59.8 | 34.1 | 37.3 |
| Phase B (QLoRA) | selective | 61.6 | 67.0 | 52.4 | 37.3 |
| Phase B (QLoRA) | oracle | 76.0 | 75.9 | 20.7 | 21.6 |

### OOD by kind of shift, retrieved top 3 policies (the full system)

| Model | Setting | Shift | Records | Accuracy | Unsafe action | Checks / case |
|---|---|---|---|---|---|---|
| Base Qwen3-8B | never | new tools + new wording, style, values | 42 | 45.2 | 20.0 | 0.00 |
| Base Qwen3-8B | never | new wording, style, values | 70 | 42.9 | 30.8 | 0.00 |
| Base Qwen3-8B | always | new tools + new wording, style, values | 42 | 54.8 | 36.0 | 3.00 |
| Base Qwen3-8B | always | new wording, style, values | 70 | 45.7 | 42.3 | 5.40 |
| Base Qwen3-8B | selective | new tools + new wording, style, values | 42 | 38.1 | 24.0 | 0.36 |
| Base Qwen3-8B | selective | new wording, style, values | 70 | 51.4 | 26.9 | 0.17 |
| Phase B (QLoRA) | never | new tools + new wording, style, values | 42 | 54.8 | 20.0 | 0.00 |
| Phase B (QLoRA) | never | new wording, style, values | 70 | 64.3 | 30.8 | 0.00 |
| Phase B (QLoRA) | always | new tools + new wording, style, values | 42 | 61.9 | 44.0 | 3.00 |
| Phase B (QLoRA) | always | new wording, style, values | 70 | 58.6 | 30.8 | 5.40 |
| Phase B (QLoRA) | selective | new tools + new wording, style, values | 42 | 59.5 | 44.0 | 0.79 |
| Phase B (QLoRA) | selective | new wording, style, values | 70 | 71.4 | 30.8 | 0.74 |

### OOD, gold policies + 2 look-alikes (retrieval assumed perfect)

112 records. Rates in %, accuracy with a 95% bootstrap interval over seeds (2000 resamples).

| Method | Setting | Accuracy [95% CI] | Unsafe action | Wrong block | Decision macro-F1 | Checks / case | Saving vs always | Check precision | Check recall | Right missing fact | Invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rules only | never | 54.5 [45.2, 62.7] | 100.0 | 0.0 | 17.6 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Rules + environment | always | 54.5 [41.2, 67.5] | 31.4 | 45.9 | 34.3 | 4.50 | 0.0 | 63.4 | 100.0 | 97.2 | 0 |
| Base Qwen3-8B | never | 48.2 [38.9, 57.5] | 13.7 | 63.9 | 36.9 | 0.00 | 100.0 | – | 0.0 | – | 1 |
| Base Qwen3-8B | always | 55.4 [44.3, 66.3] | 19.6 | 44.3 | 29.8 | 4.50 | 0.0 | 63.4 | 100.0 | 97.2 | 0 |
| Base Qwen3-8B | selective | 58.0 [47.2, 68.9] | 5.9 | 52.5 | 41.0 | 0.25 | 94.4 | 88.9 | 33.8 | 75.0 | 0 |
| Base Qwen3-8B | oracle | 63.4 [52.0, 74.5] | 3.9 | 37.7 | 44.3 | 0.65 | 85.5 | 100.0 | 100.0 | 100.0 | 1 |
| Phase B (QLoRA) | never | 67.9 [58.3, 77.2] | 23.5 | 31.1 | 60.5 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Phase B (QLoRA) | always | 66.1 [56.2, 75.5] | 19.6 | 27.9 | 46.4 | 4.50 | 0.0 | 63.4 | 100.0 | 97.2 | 0 |
| Phase B (QLoRA) | selective | 78.6 [68.2, 87.5] | 15.7 | 16.4 | 55.9 | 0.71 | 84.3 | 89.0 | 91.5 | 80.0 | 0 |
| Phase B (QLoRA) | oracle | 87.5 [80.2, 93.9] | 3.9 | 9.8 | 71.5 | 0.65 | 85.5 | 100.0 | 100.0 | 100.0 | 0 |

**Selective vs always** (R10.4: selective is not less safe than always if the upper bound of Δ unsafe-action rate (selective − always) is at most 5 points):

| Model | Δ unsafe action [95% CI] | Hypothesis | Δ accuracy [95% CI] | McNemar p (accuracy) | Checks / case, selective vs always |
|---|---|---|---|---|---|
| Base Qwen3-8B | -13.7 [-27.7, -1.8] (margin 5.0) | **passes** | 2.7 [-7.7, 13.3] | 0.701 | 0.25 vs 4.50 (p < 0.001) |
| Phase B (QLoRA) | -3.9 [-17.0, 8.9] (margin 5.0) | fails | 12.5 [1.0, 23.8] | 0.020 | 0.71 vs 4.50 (p < 0.001) |

### OOD next to in-domain test, gold policies + 2 look-alikes (retrieval assumed perfect)

| Model | Setting | Test accuracy | OOD accuracy | Test unsafe | OOD unsafe |
|---|---|---|---|---|---|
| Base Qwen3-8B | never | 34.2 | 48.2 | 23.2 | 13.7 |
| Base Qwen3-8B | always | 52.1 | 55.4 | 12.2 | 19.6 |
| Base Qwen3-8B | selective | 43.8 | 58.0 | 24.4 | 5.9 |
| Base Qwen3-8B | oracle | 51.4 | 63.4 | 6.1 | 3.9 |
| Phase B (QLoRA) | never | 61.0 | 67.9 | 29.3 | 23.5 |
| Phase B (QLoRA) | always | 75.3 | 66.1 | 12.2 | 19.6 |
| Phase B (QLoRA) | selective | 69.2 | 78.6 | 41.5 | 15.7 |
| Phase B (QLoRA) | oracle | 86.3 | 87.5 | 3.7 | 3.9 |

### OOD by kind of shift, gold policies + 2 look-alikes (retrieval assumed perfect)

| Model | Setting | Shift | Records | Accuracy | Unsafe action | Checks / case |
|---|---|---|---|---|---|---|
| Base Qwen3-8B | never | new tools + new wording, style, values | 42 | 45.2 | 16.0 | 0.00 |
| Base Qwen3-8B | never | new wording, style, values | 70 | 50.0 | 11.5 | 0.00 |
| Base Qwen3-8B | always | new tools + new wording, style, values | 42 | 64.3 | 12.0 | 3.00 |
| Base Qwen3-8B | always | new wording, style, values | 70 | 50.0 | 26.9 | 5.40 |
| Base Qwen3-8B | selective | new tools + new wording, style, values | 42 | 50.0 | 12.0 | 0.31 |
| Base Qwen3-8B | selective | new wording, style, values | 70 | 62.9 | 0.0 | 0.21 |
| Phase B (QLoRA) | never | new tools + new wording, style, values | 42 | 66.7 | 24.0 | 0.00 |
| Phase B (QLoRA) | never | new wording, style, values | 70 | 68.6 | 23.1 | 0.00 |
| Phase B (QLoRA) | always | new tools + new wording, style, values | 42 | 73.8 | 24.0 | 3.00 |
| Phase B (QLoRA) | always | new wording, style, values | 70 | 61.4 | 15.4 | 5.40 |
| Phase B (QLoRA) | selective | new tools + new wording, style, values | 42 | 73.8 | 20.0 | 0.76 |
| Phase B (QLoRA) | selective | new wording, style, values | 70 | 81.4 | 11.5 | 0.67 |
