# Results: OOD records

Monitor: Qwen3-8B, base and with the Phase B QLoRA adapter, in 4 settings (never / always / selective / oracle), next to two rule baselines (rules only = never check, rules + environment = always check). Test is the locked in-domain test set (phase 1 records), OOD the locked out-of-domain test set; nothing was tuned on them. Definitions: docs/evaluation_metrics.md; runs: kaggle/our_eval_final_*, src/baselines/run.py.

## OOD

### OOD, retrieved top 3 policies (the full system)

112 records. Rates in %, accuracy with a 95% bootstrap interval over seeds (2000 resamples).

| Method | Setting | Accuracy [95% CI] | Unsafe action | Wrong block | Decision macro-F1 | Checks / case | Saving vs always | Check precision | Check recall | Right missing fact | Invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rules only | never | 54.5 [45.2, 62.7] | 100.0 | 0.0 | 17.6 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Rules + environment | always | 47.3 [35.8, 58.5] | 52.9 | 41.0 | 29.0 | 4.50 | 0.0 | 63.4 | 100.0 | 97.2 | 0 |
| Base Qwen3-8B | never | 43.8 [34.9, 52.7] | 25.5 | 60.7 | 29.1 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Base Qwen3-8B | always | 48.2 [39.1, 57.3] | 39.2 | 47.5 | 25.9 | 4.50 | 0.0 | 63.4 | 100.0 | 97.2 | 0 |
| Base Qwen3-8B | selective | 45.5 [36.8, 54.5] | 29.4 | 60.7 | 30.2 | 0.26 | 94.2 | 78.6 | 31.0 | 45.5 | 1 |
| Base Qwen3-8B | oracle | 54.5 [42.7, 65.7] | 19.6 | 45.9 | 34.0 | 0.65 | 85.5 | 100.0 | 100.0 | 100.0 | 0 |
| Phase B (QLoRA) | never | 57.1 [46.5, 66.9] | 21.6 | 47.5 | 37.2 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Phase B (QLoRA) | always | 61.6 [50.9, 72.2] | 39.2 | 23.0 | 40.7 | 4.50 | 0.0 | 63.4 | 100.0 | 97.2 | 0 |
| Phase B (QLoRA) | selective | 67.9 [56.9, 77.6] | 31.4 | 21.3 | 39.4 | 0.71 | 84.1 | 84.8 | 94.4 | 55.2 | 1 |
| Phase B (QLoRA) | oracle | 77.7 [67.9, 86.6] | 11.8 | 16.4 | 47.9 | 0.65 | 85.5 | 100.0 | 100.0 | 100.0 | 0 |

**Selective vs always** (R10.4: selective is not less safe than always if the upper bound of Δ unsafe-action rate (selective − always) is at most 5 points):

| Model | Δ unsafe action [95% CI] | Hypothesis | Δ accuracy [95% CI] | McNemar p (accuracy) | Checks / case, selective vs always |
|---|---|---|---|---|---|
| Base Qwen3-8B | -9.8 [-26.7, 7.7] (margin 5.0) | fails | -2.7 [-13.0, 7.4] | 0.720 | 0.26 vs 4.50 (p < 0.001) |
| Phase B (QLoRA) | -7.8 [-28.6, 13.0] (margin 5.0) | fails | 6.2 [-7.4, 19.4] | 0.324 | 0.71 vs 4.50 (p < 0.001) |

### OOD next to in-domain test, retrieved top 3 policies (the full system)

| Model | Setting | Test accuracy | OOD accuracy | Test unsafe | OOD unsafe |
|---|---|---|---|---|---|
| Base Qwen3-8B | never | 40.0 | 43.8 | 30.4 | 25.5 |
| Base Qwen3-8B | always | 63.3 | 48.2 | 10.7 | 39.2 |
| Base Qwen3-8B | selective | 52.5 | 45.5 | 25.0 | 29.4 |
| Base Qwen3-8B | oracle | 58.3 | 54.5 | 10.7 | 19.6 |
| Phase B (QLoRA) | never | 56.7 | 57.1 | 21.4 | 21.6 |
| Phase B (QLoRA) | always | 76.7 | 61.6 | 26.8 | 39.2 |
| Phase B (QLoRA) | selective | 74.2 | 67.9 | 32.1 | 31.4 |
| Phase B (QLoRA) | oracle | 81.7 | 77.7 | 16.1 | 11.8 |

### OOD by kind of shift, retrieved top 3 policies (the full system)

| Model | Setting | Shift | Records | Accuracy | Unsafe action | Checks / case |
|---|---|---|---|---|---|---|
| Base Qwen3-8B | never | new tools + new wording, style, values | 42 | 45.2 | 20.0 | 0.00 |
| Base Qwen3-8B | never | new wording, style, values | 70 | 42.9 | 30.8 | 0.00 |
| Base Qwen3-8B | always | new tools + new wording, style, values | 42 | 54.8 | 36.0 | 3.00 |
| Base Qwen3-8B | always | new wording, style, values | 70 | 44.3 | 42.3 | 5.40 |
| Base Qwen3-8B | selective | new tools + new wording, style, values | 42 | 38.1 | 32.0 | 0.43 |
| Base Qwen3-8B | selective | new wording, style, values | 70 | 50.0 | 26.9 | 0.16 |
| Phase B (QLoRA) | never | new tools + new wording, style, values | 42 | 50.0 | 20.0 | 0.00 |
| Phase B (QLoRA) | never | new wording, style, values | 70 | 61.4 | 23.1 | 0.00 |
| Phase B (QLoRA) | always | new tools + new wording, style, values | 42 | 64.3 | 44.0 | 3.00 |
| Phase B (QLoRA) | always | new wording, style, values | 70 | 60.0 | 34.6 | 5.40 |
| Phase B (QLoRA) | selective | new tools + new wording, style, values | 42 | 45.2 | 40.0 | 0.69 |
| Phase B (QLoRA) | selective | new wording, style, values | 70 | 81.4 | 23.1 | 0.73 |

### OOD, gold policies + 2 look-alikes (retrieval assumed perfect)

112 records. Rates in %, accuracy with a 95% bootstrap interval over seeds (2000 resamples).

| Method | Setting | Accuracy [95% CI] | Unsafe action | Wrong block | Decision macro-F1 | Checks / case | Saving vs always | Check precision | Check recall | Right missing fact | Invalid |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Rules only | never | 54.5 [45.2, 62.7] | 100.0 | 0.0 | 17.6 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Rules + environment | always | 55.4 [42.1, 68.9] | 31.4 | 44.3 | 34.8 | 4.50 | 0.0 | 63.4 | 100.0 | 97.2 | 0 |
| Base Qwen3-8B | never | 47.3 [38.0, 56.9] | 15.7 | 63.9 | 35.8 | 0.00 | 100.0 | – | 0.0 | – | 1 |
| Base Qwen3-8B | always | 55.4 [44.3, 66.3] | 19.6 | 44.3 | 29.8 | 4.50 | 0.0 | 63.4 | 100.0 | 97.2 | 0 |
| Base Qwen3-8B | selective | 60.7 [49.1, 71.8] | 5.9 | 49.2 | 44.7 | 0.29 | 93.7 | 86.7 | 36.6 | 65.4 | 0 |
| Base Qwen3-8B | oracle | 63.4 [52.0, 74.5] | 3.9 | 37.7 | 44.3 | 0.65 | 85.5 | 100.0 | 100.0 | 100.0 | 1 |
| Phase B (QLoRA) | never | 63.4 [52.9, 72.7] | 13.7 | 39.3 | 40.4 | 0.00 | 100.0 | – | 0.0 | – | 0 |
| Phase B (QLoRA) | always | 68.8 [58.2, 78.7] | 17.6 | 23.0 | 45.3 | 4.50 | 0.0 | 63.4 | 100.0 | 97.2 | 0 |
| Phase B (QLoRA) | selective | 83.9 [75.5, 91.5] | 11.8 | 6.6 | 63.5 | 0.69 | 84.7 | 90.8 | 97.2 | 82.6 | 1 |
| Phase B (QLoRA) | oracle | 86.6 [77.4, 94.1] | 2.0 | 4.9 | 64.7 | 0.65 | 85.5 | 100.0 | 100.0 | 100.0 | 0 |

**Selective vs always** (R10.4: selective is not less safe than always if the upper bound of Δ unsafe-action rate (selective − always) is at most 5 points):

| Model | Δ unsafe action [95% CI] | Hypothesis | Δ accuracy [95% CI] | McNemar p (accuracy) | Checks / case, selective vs always |
|---|---|---|---|---|---|
| Base Qwen3-8B | -13.7 [-28.6, 0.0] (margin 5.0) | **passes** | 5.4 [-4.5, 15.5] | 0.307 | 0.29 vs 4.50 (p < 0.001) |
| Phase B (QLoRA) | -5.9 [-21.2, 8.7] (margin 5.0) | fails | 15.2 [4.1, 25.9] | 0.002 | 0.69 vs 4.50 (p < 0.001) |

### OOD next to in-domain test, gold policies + 2 look-alikes (retrieval assumed perfect)

| Model | Setting | Test accuracy | OOD accuracy | Test unsafe | OOD unsafe |
|---|---|---|---|---|---|
| Base Qwen3-8B | never | 40.0 | 47.3 | 16.1 | 15.7 |
| Base Qwen3-8B | always | 61.7 | 55.4 | 7.1 | 19.6 |
| Base Qwen3-8B | selective | 55.8 | 60.7 | 10.7 | 5.9 |
| Base Qwen3-8B | oracle | 61.7 | 63.4 | 1.8 | 3.9 |
| Phase B (QLoRA) | never | 60.0 | 63.4 | 14.3 | 13.7 |
| Phase B (QLoRA) | always | 80.0 | 68.8 | 8.9 | 17.6 |
| Phase B (QLoRA) | selective | 79.2 | 83.9 | 25.0 | 11.8 |
| Phase B (QLoRA) | oracle | 84.2 | 86.6 | 3.6 | 2.0 |

### OOD by kind of shift, gold policies + 2 look-alikes (retrieval assumed perfect)

| Model | Setting | Shift | Records | Accuracy | Unsafe action | Checks / case |
|---|---|---|---|---|---|---|
| Base Qwen3-8B | never | new tools + new wording, style, values | 42 | 45.2 | 16.0 | 0.00 |
| Base Qwen3-8B | never | new wording, style, values | 70 | 48.6 | 15.4 | 0.00 |
| Base Qwen3-8B | always | new tools + new wording, style, values | 42 | 64.3 | 12.0 | 3.00 |
| Base Qwen3-8B | always | new wording, style, values | 70 | 50.0 | 26.9 | 5.40 |
| Base Qwen3-8B | selective | new tools + new wording, style, values | 42 | 57.1 | 12.0 | 0.43 |
| Base Qwen3-8B | selective | new wording, style, values | 70 | 62.9 | 0.0 | 0.20 |
| Phase B (QLoRA) | never | new tools + new wording, style, values | 42 | 57.1 | 16.0 | 0.00 |
| Phase B (QLoRA) | never | new wording, style, values | 70 | 67.1 | 11.5 | 0.00 |
| Phase B (QLoRA) | always | new tools + new wording, style, values | 42 | 73.8 | 20.0 | 3.00 |
| Phase B (QLoRA) | always | new wording, style, values | 70 | 65.7 | 15.4 | 5.40 |
| Phase B (QLoRA) | selective | new tools + new wording, style, values | 42 | 66.7 | 24.0 | 0.67 |
| Phase B (QLoRA) | selective | new wording, style, values | 70 | 94.3 | 0.0 | 0.70 |
