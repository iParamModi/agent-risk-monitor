# Results: Val, Test, OOD records (system v2)

Monitor: Qwen3-8B, base and with the Phase B QLoRA adapter, in 4 settings (never / always / selective / oracle), next to two rule baselines (rules only = never check, rules + environment = always check). Test is the locked in-domain test set (phase 1 records), OOD the locked out-of-domain test set; nothing was tuned on them. Definitions: docs/evaluation_metrics.md; runs: kaggle/our_eval_final_*, src/baselines/run.py.

**System v2** (decisions.md 2026-11-11): retrieval looks only at the policies tagged with the proposed action's tool and shows 8; selective adds the second-source check and two prompt hints. Same adapter, no retraining. With correct policies only selective changes; the other settings are the v1 runs.

## Val

### Val, retrieved policies, tag-filtered top 8 (the full system)

40 records. Rates in %, accuracy with a 95% bootstrap interval over seeds (2000 resamples).

| Method | Setting | Accuracy [95% CI] | Unsafe action | Wrong block | Decision macro-F1 | Checks / case | Saving vs always | Check precision | Check recall | Right missing fact | Invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rules only | never | 57.5 [42.1, 69.0] | 89.5 | 0.0 | 30.7 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Rules + environment | always | 67.5 [47.5, 86.1] | 26.3 | 23.8 | 63.8 | 5.00 | 0.0 | 70.0 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | never | 55.0 [42.1, 68.4] | 21.1 | 47.6 | 29.6 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Base Qwen3-8B | always | 80.0 [61.8, 93.2] | 26.3 | 4.8 | 41.4 | 5.00 | 0.0 | 70.0 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | selective | 65.0 [50.0, 80.0] | 26.3 | 28.6 | 35.7 | 0.62 | 87.5 | 66.7 | 42.9 | 58.3 | 1 |
| Base Qwen3-8B | oracle | 67.5 [50.0, 84.2] | 21.1 | 14.3 | 38.6 | 0.75 | 85.0 | 100.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | never | 72.5 [52.9, 87.0] | 36.8 | 9.5 | 36.8 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Phase B (QLoRA) | always | 70.0 [50.0, 84.8] | 36.8 | 0.0 | 46.5 | 5.00 | 0.0 | 70.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | selective | 77.5 [62.5, 90.5] | 42.1 | 4.8 | 82.8 | 0.85 | 83.0 | 88.9 | 85.7 | 62.5 | 0 |
| Phase B (QLoRA) | oracle | 90.0 [76.3, 100.0] | 21.1 | 0.0 | 70.0 | 0.75 | 85.0 | 100.0 | 100.0 | 100.0 | 0 |

**Selective vs always** (R10.4: selective is not less safe than always if the upper bound of Δ unsafe-action rate (selective − always) is at most 5 points):

| Model | Δ unsafe action [95% CI] | Hypothesis | Δ accuracy [95% CI] | McNemar p (accuracy) | Checks / case, selective vs always |
|---|---|---|---|---|---|
| Base Qwen3-8B | 0.0 [-25.0, 23.5] (margin 5.0) | fails | -15.0 [-34.2, 7.1] | 0.146 | 0.62 vs 5.00 (p < 0.001) |
| Phase B (QLoRA) | 5.3 [-23.5, 31.2] (margin 5.0) | fails | 7.5 [-8.3, 27.5] | 0.508 | 0.85 vs 5.00 (p < 0.001) |

### Val, gold policies + 2 look-alikes (retrieval assumed perfect)

40 records. Rates in %, accuracy with a 95% bootstrap interval over seeds (2000 resamples).

| Method | Setting | Accuracy [95% CI] | Unsafe action | Wrong block | Decision macro-F1 | Checks / case | Saving vs always | Check precision | Check recall | Right missing fact | Invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rules only | never | 57.5 [42.1, 69.0] | 89.5 | 0.0 | 30.7 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Rules + environment | always | 65.0 [42.5, 86.1] | 21.1 | 33.3 | 62.6 | 5.00 | 0.0 | 70.0 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | never | 57.5 [41.2, 72.7] | 31.6 | 28.6 | 32.4 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Base Qwen3-8B | always | 75.0 [57.5, 89.5] | 26.3 | 0.0 | 40.3 | 5.00 | 0.0 | 70.0 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | selective | 65.0 [47.5, 81.6] | 42.1 | 19.0 | 34.6 | 0.33 | 93.5 | 75.0 | 32.1 | 55.6 | 0 |
| Base Qwen3-8B | oracle | 80.0 [63.2, 92.5] | 21.1 | 9.5 | 43.1 | 0.75 | 85.0 | 100.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | never | 75.0 [55.6, 89.1] | 47.4 | 4.8 | 39.1 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Phase B (QLoRA) | always | 82.5 [65.8, 93.5] | 26.3 | 0.0 | 42.2 | 5.00 | 0.0 | 70.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | selective | 85.0 [75.0, 94.7] | 26.3 | 4.8 | 89.0 | 0.72 | 85.5 | 95.8 | 82.1 | 78.3 | 0 |
| Phase B (QLoRA) | oracle | 97.5 [91.7, 100.0] | 5.3 | 0.0 | 74.2 | 0.75 | 85.0 | 100.0 | 100.0 | 100.0 | 0 |

**Selective vs always** (R10.4: selective is not less safe than always if the upper bound of Δ unsafe-action rate (selective − always) is at most 5 points):

| Model | Δ unsafe action [95% CI] | Hypothesis | Δ accuracy [95% CI] | McNemar p (accuracy) | Checks / case, selective vs always |
|---|---|---|---|---|---|
| Base Qwen3-8B | 15.8 [-6.2, 44.4] (margin 5.0) | fails | -10.0 [-30.0, 10.5] | 0.344 | 0.33 vs 5.00 (p < 0.001) |
| Phase B (QLoRA) | 0.0 [-21.1, 21.1] (margin 5.0) | fails | 2.5 [-10.5, 19.4] | 1.000 | 0.72 vs 5.00 (p < 0.001) |

## Test

### Test, retrieved policies, tag-filtered top 8 (the full system)

146 records. Rates in %, accuracy with a 95% bootstrap interval over seeds (2000 resamples).

| Method | Setting | Accuracy [95% CI] | Unsafe action | Wrong block | Decision macro-F1 | Checks / case | Saving vs always | Check precision | Check recall | Right missing fact | Invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rules only | never | 44.5 [34.8, 53.2] | 93.9 | 0.0 | 16.8 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Rules + environment | always | 46.6 [35.4, 57.6] | 28.0 | 53.1 | 36.1 | 4.82 | 0.0 | 73.3 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | never | 36.3 [28.1, 44.3] | 15.9 | 54.7 | 25.4 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Base Qwen3-8B | always | 54.8 [44.2, 65.4] | 24.4 | 18.8 | 39.1 | 4.82 | 0.0 | 73.3 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | selective | 44.5 [34.9, 53.5] | 26.8 | 40.6 | 32.4 | 0.61 | 87.4 | 93.3 | 65.4 | 62.9 | 5 |
| Base Qwen3-8B | oracle | 50.0 [39.9, 59.3] | 8.5 | 32.8 | 35.9 | 0.97 | 80.0 | 100.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | never | 58.2 [46.1, 68.8] | 30.5 | 7.8 | 36.6 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Phase B (QLoRA) | always | 62.3 [52.2, 71.3] | 24.4 | 4.7 | 42.0 | 4.82 | 0.0 | 73.3 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | selective | 63.0 [50.8, 73.3] | 39.0 | 6.2 | 39.3 | 0.80 | 83.4 | 97.1 | 95.3 | 70.6 | 0 |
| Phase B (QLoRA) | oracle | 80.8 [72.1, 88.2] | 15.9 | 1.6 | 60.1 | 0.97 | 80.0 | 100.0 | 100.0 | 100.0 | 0 |

**Selective vs always** (R10.4: selective is not less safe than always if the upper bound of Δ unsafe-action rate (selective − always) is at most 5 points):

| Model | Δ unsafe action [95% CI] | Hypothesis | Δ accuracy [95% CI] | McNemar p (accuracy) | Checks / case, selective vs always |
|---|---|---|---|---|---|
| Base Qwen3-8B | 2.4 [-10.1, 14.9] (margin 5.0) | fails | -10.3 [-18.7, -2.2] | 0.011 | 0.61 vs 4.82 (p < 0.001) |
| Phase B (QLoRA) | 14.6 [0.0, 29.7] (margin 5.0) | fails | 0.7 [-7.7, 8.6] | 1.000 | 0.80 vs 4.82 (p < 0.001) |

### Test, gold policies + 2 look-alikes (retrieval assumed perfect)

146 records. Rates in %, accuracy with a 95% bootstrap interval over seeds (2000 resamples).

| Method | Setting | Accuracy [95% CI] | Unsafe action | Wrong block | Decision macro-F1 | Checks / case | Saving vs always | Check precision | Check recall | Right missing fact | Invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rules only | never | 43.8 [34.3, 52.5] | 95.1 | 1.6 | 16.6 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Rules + environment | always | 52.1 [39.9, 63.6] | 28.0 | 40.6 | 39.4 | 4.82 | 0.0 | 73.3 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | never | 34.2 [26.8, 41.4] | 23.2 | 59.4 | 23.5 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Base Qwen3-8B | always | 52.1 [41.8, 62.5] | 12.2 | 29.7 | 42.0 | 4.82 | 0.0 | 73.3 | 100.0 | 100.0 | 0 |
| Base Qwen3-8B | selective | 43.2 [34.7, 51.4] | 26.8 | 43.8 | 30.3 | 0.58 | 88.1 | 89.3 | 62.6 | 67.2 | 1 |
| Base Qwen3-8B | oracle | 51.4 [41.3, 60.6] | 6.1 | 31.2 | 39.4 | 0.97 | 80.0 | 100.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | never | 61.0 [49.3, 70.9] | 29.3 | 14.1 | 44.5 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Phase B (QLoRA) | always | 75.3 [65.4, 84.0] | 12.2 | 4.7 | 63.5 | 4.82 | 0.0 | 73.3 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | selective | 69.9 [59.0, 79.6] | 39.0 | 3.1 | 48.0 | 0.74 | 84.7 | 96.0 | 90.7 | 78.4 | 0 |
| Phase B (QLoRA) | oracle | 86.3 [79.2, 92.3] | 3.7 | 1.6 | 64.3 | 0.97 | 80.0 | 100.0 | 100.0 | 100.0 | 0 |

**Selective vs always** (R10.4: selective is not less safe than always if the upper bound of Δ unsafe-action rate (selective − always) is at most 5 points):

| Model | Δ unsafe action [95% CI] | Hypothesis | Δ accuracy [95% CI] | McNemar p (accuracy) | Checks / case, selective vs always |
|---|---|---|---|---|---|
| Base Qwen3-8B | 14.6 [3.5, 26.2] (margin 5.0) | fails | -8.9 [-16.9, -2.0] | 0.015 | 0.58 vs 4.82 (p < 0.001) |
| Phase B (QLoRA) | 26.8 [14.3, 39.5] (margin 5.0) | fails | -5.5 [-15.0, 3.4] | 0.200 | 0.74 vs 4.82 (p < 0.001) |

## OOD

### OOD, retrieved policies, tag-filtered top 8 (the full system)

112 records. Rates in %, accuracy with a 95% bootstrap interval over seeds (2000 resamples).

| Method | Setting | Accuracy [95% CI] | Unsafe action | Wrong block | Decision macro-F1 | Checks / case | Saving vs always | Check precision | Check recall | Right missing fact | Invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rules only | never | 53.6 [44.3, 61.6] | 100.0 | 1.6 | 17.4 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Rules + environment | always | 48.2 [36.4, 61.2] | 27.5 | 55.7 | 30.8 | 4.50 | 0.0 | 63.4 | 100.0 | 97.2 | 0 |
| Base Qwen3-8B | never | 48.2 [38.4, 57.7] | 11.8 | 60.7 | 30.7 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Base Qwen3-8B | always | 58.9 [50.0, 68.2] | 23.5 | 41.0 | 31.5 | 4.50 | 0.0 | 63.4 | 100.0 | 97.2 | 0 |
| Base Qwen3-8B | selective | 50.0 [40.8, 59.4] | 11.8 | 59.0 | 27.2 | 0.44 | 90.3 | 79.1 | 47.9 | 41.2 | 1 |
| Base Qwen3-8B | oracle | 65.2 [53.8, 76.4] | 3.9 | 36.1 | 42.3 | 0.65 | 85.5 | 100.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | never | 68.8 [58.8, 78.2] | 19.6 | 32.8 | 52.8 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Phase B (QLoRA) | always | 63.4 [53.9, 73.2] | 29.4 | 23.0 | 39.9 | 4.50 | 0.0 | 63.4 | 100.0 | 97.2 | 0 |
| Phase B (QLoRA) | selective | 66.1 [54.8, 76.3] | 35.3 | 18.0 | 47.7 | 0.68 | 84.9 | 87.3 | 87.3 | 64.5 | 1 |
| Phase B (QLoRA) | oracle | 82.1 [73.6, 89.7] | 5.9 | 13.1 | 58.9 | 0.65 | 85.5 | 100.0 | 100.0 | 100.0 | 0 |

**Selective vs always** (R10.4: selective is not less safe than always if the upper bound of Δ unsafe-action rate (selective − always) is at most 5 points):

| Model | Δ unsafe action [95% CI] | Hypothesis | Δ accuracy [95% CI] | McNemar p (accuracy) | Checks / case, selective vs always |
|---|---|---|---|---|---|
| Base Qwen3-8B | -11.8 [-26.4, 2.3] (margin 5.0) | **passes** | -8.9 [-18.2, 0.0] | 0.110 | 0.44 vs 4.50 (p < 0.001) |
| Phase B (QLoRA) | 5.9 [-10.9, 23.3] (margin 5.0) | fails | 2.7 [-9.5, 14.9] | 0.728 | 0.68 vs 4.50 (p < 0.001) |

### OOD next to in-domain test, retrieved policies, tag-filtered top 8 (the full system)

| Model | Setting | Test accuracy | OOD accuracy | Test unsafe | OOD unsafe |
|---|---|---|---|---|---|
| Base Qwen3-8B | never | 36.3 | 48.2 | 15.9 | 11.8 |
| Base Qwen3-8B | always | 54.8 | 58.9 | 24.4 | 23.5 |
| Base Qwen3-8B | selective | 44.5 | 50.0 | 26.8 | 11.8 |
| Base Qwen3-8B | oracle | 50.0 | 65.2 | 8.5 | 3.9 |
| Phase B (QLoRA) | never | 58.2 | 68.8 | 30.5 | 19.6 |
| Phase B (QLoRA) | always | 62.3 | 63.4 | 24.4 | 29.4 |
| Phase B (QLoRA) | selective | 63.0 | 66.1 | 39.0 | 35.3 |
| Phase B (QLoRA) | oracle | 80.8 | 82.1 | 15.9 | 5.9 |

### OOD by kind of shift, retrieved policies, tag-filtered top 8 (the full system)

| Model | Setting | Shift | Records | Accuracy | Unsafe action | Checks / case |
|---|---|---|---|---|---|---|
| Base Qwen3-8B | never | new tools + new wording, style, values | 42 | 40.5 | 12.0 | 0.00 |
| Base Qwen3-8B | never | new wording, style, values | 70 | 52.9 | 11.5 | 0.00 |
| Base Qwen3-8B | always | new tools + new wording, style, values | 42 | 61.9 | 28.0 | 3.00 |
| Base Qwen3-8B | always | new wording, style, values | 70 | 57.1 | 19.2 | 5.40 |
| Base Qwen3-8B | selective | new tools + new wording, style, values | 42 | 50.0 | 8.0 | 0.52 |
| Base Qwen3-8B | selective | new wording, style, values | 70 | 50.0 | 15.4 | 0.39 |
| Phase B (QLoRA) | never | new tools + new wording, style, values | 42 | 76.2 | 20.0 | 0.00 |
| Phase B (QLoRA) | never | new wording, style, values | 70 | 64.3 | 19.2 | 0.00 |
| Phase B (QLoRA) | always | new tools + new wording, style, values | 42 | 61.9 | 36.0 | 3.00 |
| Phase B (QLoRA) | always | new wording, style, values | 70 | 64.3 | 23.1 | 5.40 |
| Phase B (QLoRA) | selective | new tools + new wording, style, values | 42 | 61.9 | 36.0 | 0.76 |
| Phase B (QLoRA) | selective | new wording, style, values | 70 | 68.6 | 34.6 | 0.63 |

### OOD, gold policies + 2 look-alikes (retrieval assumed perfect)

112 records. Rates in %, accuracy with a 95% bootstrap interval over seeds (2000 resamples).

| Method | Setting | Accuracy [95% CI] | Unsafe action | Wrong block | Decision macro-F1 | Checks / case | Saving vs always | Check precision | Check recall | Right missing fact | Invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rules only | never | 54.5 [45.2, 62.7] | 100.0 | 0.0 | 17.6 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Rules + environment | always | 54.5 [41.2, 67.5] | 31.4 | 45.9 | 34.3 | 4.50 | 0.0 | 63.4 | 100.0 | 97.2 | 0 |
| Base Qwen3-8B | never | 48.2 [38.9, 57.5] | 13.7 | 63.9 | 36.9 | 0.00 | 100.0 | – | 0.0 | – | 1 |
| Base Qwen3-8B | always | 55.4 [44.3, 66.3] | 19.6 | 44.3 | 29.8 | 4.50 | 0.0 | 63.4 | 100.0 | 97.2 | 0 |
| Base Qwen3-8B | selective | 57.1 [46.4, 68.0] | 9.8 | 52.5 | 40.6 | 0.25 | 94.4 | 88.9 | 33.8 | 66.7 | 1 |
| Base Qwen3-8B | oracle | 63.4 [52.0, 74.5] | 3.9 | 37.7 | 44.3 | 0.65 | 85.5 | 100.0 | 100.0 | 100.0 | 1 |
| Phase B (QLoRA) | never | 67.9 [58.3, 77.2] | 23.5 | 31.1 | 60.5 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Phase B (QLoRA) | always | 66.1 [56.2, 75.5] | 19.6 | 27.9 | 46.4 | 4.50 | 0.0 | 63.4 | 100.0 | 97.2 | 0 |
| Phase B (QLoRA) | selective | 80.4 [71.5, 88.0] | 15.7 | 14.8 | 58.5 | 0.68 | 84.9 | 88.7 | 88.7 | 82.5 | 0 |
| Phase B (QLoRA) | oracle | 87.5 [80.2, 93.9] | 3.9 | 9.8 | 71.5 | 0.65 | 85.5 | 100.0 | 100.0 | 100.0 | 0 |

**Selective vs always** (R10.4: selective is not less safe than always if the upper bound of Δ unsafe-action rate (selective − always) is at most 5 points):

| Model | Δ unsafe action [95% CI] | Hypothesis | Δ accuracy [95% CI] | McNemar p (accuracy) | Checks / case, selective vs always |
|---|---|---|---|---|---|
| Base Qwen3-8B | -9.8 [-28.0, 5.9] (margin 5.0) | fails | 1.8 [-8.8, 12.7] | 0.851 | 0.25 vs 4.50 (p < 0.001) |
| Phase B (QLoRA) | -3.9 [-16.4, 9.1] (margin 5.0) | fails | 14.3 [3.4, 25.0] | 0.009 | 0.68 vs 4.50 (p < 0.001) |

### OOD next to in-domain test, gold policies + 2 look-alikes (retrieval assumed perfect)

| Model | Setting | Test accuracy | OOD accuracy | Test unsafe | OOD unsafe |
|---|---|---|---|---|---|
| Base Qwen3-8B | never | 34.2 | 48.2 | 23.2 | 13.7 |
| Base Qwen3-8B | always | 52.1 | 55.4 | 12.2 | 19.6 |
| Base Qwen3-8B | selective | 43.2 | 57.1 | 26.8 | 9.8 |
| Base Qwen3-8B | oracle | 51.4 | 63.4 | 6.1 | 3.9 |
| Phase B (QLoRA) | never | 61.0 | 67.9 | 29.3 | 23.5 |
| Phase B (QLoRA) | always | 75.3 | 66.1 | 12.2 | 19.6 |
| Phase B (QLoRA) | selective | 69.9 | 80.4 | 39.0 | 15.7 |
| Phase B (QLoRA) | oracle | 86.3 | 87.5 | 3.7 | 3.9 |

### OOD by kind of shift, gold policies + 2 look-alikes (retrieval assumed perfect)

| Model | Setting | Shift | Records | Accuracy | Unsafe action | Checks / case |
|---|---|---|---|---|---|---|
| Base Qwen3-8B | never | new tools + new wording, style, values | 42 | 45.2 | 16.0 | 0.00 |
| Base Qwen3-8B | never | new wording, style, values | 70 | 50.0 | 11.5 | 0.00 |
| Base Qwen3-8B | always | new tools + new wording, style, values | 42 | 64.3 | 12.0 | 3.00 |
| Base Qwen3-8B | always | new wording, style, values | 70 | 50.0 | 26.9 | 5.40 |
| Base Qwen3-8B | selective | new tools + new wording, style, values | 42 | 47.6 | 20.0 | 0.33 |
| Base Qwen3-8B | selective | new wording, style, values | 70 | 62.9 | 0.0 | 0.20 |
| Phase B (QLoRA) | never | new tools + new wording, style, values | 42 | 66.7 | 24.0 | 0.00 |
| Phase B (QLoRA) | never | new wording, style, values | 70 | 68.6 | 23.1 | 0.00 |
| Phase B (QLoRA) | always | new tools + new wording, style, values | 42 | 73.8 | 24.0 | 3.00 |
| Phase B (QLoRA) | always | new wording, style, values | 70 | 61.4 | 15.4 | 5.40 |
| Phase B (QLoRA) | selective | new tools + new wording, style, values | 42 | 78.6 | 16.0 | 0.74 |
| Phase B (QLoRA) | selective | new wording, style, values | 70 | 81.4 | 15.4 | 0.64 |
