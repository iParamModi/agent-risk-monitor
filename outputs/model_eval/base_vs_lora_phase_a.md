# Base vs fine-tuned Qwen3-8B: external val (Phase A)

2026-10-27, Meet. Same 241 external val records (4 ATBench > 7,300 tokens left out), same code, float16, greedy,
setting `never` (one pass, risk answer only), Kaggle T4 x2, transformers 5.16.1, peft 0.20.0, torch 2.11.

- **Base**: `Qwen/Qwen3-8B` rev `b968826`, no training (`kaggle/base_eval/`).
- **QLoRA**: the same base + LoRA trained on `phase_a_train.txt` (`kaggle/finetune/`, R13.1: r 16, alpha 32,
  lr 2e-4, 2 epochs, 4-bit NF4). 993 of 1,034 examples kept (41 over 4,096 tokens, 37 of them ATBench UNSAFE).
  250 steps, 3 h 23 min; train loss 0.037, eval loss 0.0355 (epoch 1) → 0.0228 (epoch 2). Scored by
  `kaggle/lora_eval/` from the saved adapter (the training job's own val run stopped on a torchao clash).

Counts and scores only; predictions stay local (`outputs/kaggle/`, ignored: AgentRisk has no licence).

## Risk label

| Source | n | Base F1 | QLoRA F1 | Base accuracy | QLoRA accuracy | Unsafe caught (base → QLoRA) | Safe flagged as unsafe (base → QLoRA) |
|---|---|---|---|---|---|---|---|
| R-Judge | 47 | 45.7 | 86.5 | 59.6 | 89.4 | 8 → 16 of 21 | 6 → 0 of 26 |
| ATBench | 96 | 3.9 | 90.5 | 49.0 | 90.6 | 1 → 43 of 49 | 1 → 3 of 47 |
| AgentRisk | 98 | 4.1 | 98.9 | 52.0 | 99.0 | 1 → 47 of 48 | 0 → 0 of 50 |
| **All** | **241** | **14.8** | **93.4** | **52.3** | **93.8** | **10 → 106 of 118** | **7 → 3 of 123** |

The base model answers SAFE on 224 of 241 records.

## Risk type

| Source | Base macro-F1 | QLoRA macro-F1 | Right type on unsafe records (base → QLoRA) |
|---|---|---|---|
| R-Judge | 15.2 | 50.5 | 5 → 12 of 21 |
| ATBench | 0.0 | 52.3 | 0 → 28 of 49 |
| AgentRisk | 1.2 | 62.8 | 1 → 41 of 48 |
| **All** | **4.0** | **59.6** | **6 → 81 of 118** |

Per type, all sources (F1, base → QLoRA): PRIVACY_LEAKAGE 10.2 → 85.7, SECURITY 14.0 → 73.5, DATA_LOSS 0.0 → 66.7,
FINANCIAL_LOSS 0.0 → 50.0, OTHER 0.0 → 41.7, ACCESS_CONTROL 0.0 → 40.0. Small classes (e.g. 3 DATA_LOSS, 11
ACCESS_CONTROL unsafe val records) make these per-type numbers noisy. Most type errors: ACCESS_CONTROL read as
SECURITY / OTHER, FINANCIAL_LOSS as OTHER, SECURITY as OTHER / NONE.

## Read with care

- **ATBench shortcut**: ATBench's unsafe trajectories often carry error / injection markers that give the label away
  (known leak; distractor-turn fix planned after 30 Oct). Part of the ATBench jump may be the shortcut.
- **AgentRisk 98.9**: check for a similar surface cue before reading it as real skill (e.g. SAFE records that are
  plain replies).
- One run, one seed; no confidence intervals per source yet. Val only; test untouched.
