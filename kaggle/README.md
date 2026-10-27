# Kaggle jobs (GPU)

We have no GPU, so model runs go to Kaggle (free GPU T4 x2, 2 x 16 GB). Everything stays **private**.

| Job | Folder | What |
|---|---|---|
| 1. Base model on external val (no training) | `kaggle/base_eval/` | Qwen3-8B (float16, rev `b968826`), 241 external val records, scored with `src.eval.tables` |
| 2. Fine-tune, then the same val | `kaggle/finetune/` | QLoRA (R13.1: r 16, alpha 32, lr 2e-4, 2 epochs, 4-bit NF4) on `phase_a_train.txt` (1,034), then the same 241 val records with the adapter (float16 base + LoRA) |
| 2b. Saved adapter on the same val | `kaggle/lora_eval/` | the evaluation part of job 2 only, on an adapter uploaded as the PRIVATE dataset `meet6868/agent-risk-adapter` (a failed run's output cannot be a Kaggle input); for when training finished but evaluation did not |

Run 1 first, then 2 (Meet): comparing the two tables shows what training adds. Same records, code and precision.

## One-time setup

1. `.env` (git-ignored) holds `KAGGLE_USERNAME`, `KAGGLE_API_TOKEN`, `HF_TOKEN`. Never commit it.
2. `pip install kaggle` (CLI 2.x).

## Run

```bash
bash scripts/kaggle_push_code.sh "what changed"        # code -> private dataset <user>/agent-risk-code
set -a; . ./.env; set +a
kaggle kernels push -p kaggle/base_eval --accelerator NvidiaTeslaT4
kaggle kernels status meet6868/agent-risk-base-eval
kaggle kernels output meet6868/agent-risk-base-eval -p outputs/kaggle/base_eval   # results only
# after job 1 has finished:
kaggle kernels push -p kaggle/finetune --accelerator NvidiaTeslaT4
kaggle kernels output meet6868/agent-risk-finetune -p outputs/kaggle/finetune     # adapter + results
kaggle kernels push -p kaggle/lora_eval --accelerator NvidiaTeslaT4                # only if job 2's evaluation failed
```

## Logs

Live: `kaggle kernels logs -f <user>/<job>/<version>` (CLI 2.2+; plain `kernels logs` is empty while it runs).
The CLI cannot cancel a run and a new version does not stop the old one: stop it on the web page. Each job also writes `/kaggle/working/progress.log` (kept even if the job fails):
`[HH:MM:SS UTC] start: <step>` / `done` / `FAILED`, plus
`[train] step 120/250 (48%) | epoch 0.96 | loss 0.3120 | lr 1.8e-04 | 0h 41m elapsed, ~0h 44m left` (every 10 steps,
eval loss per epoch) and `[run] 40/241 (17%) | 6m 10s, ~31m left | invalid 2 | answer 28 tokens on average`
(every 10 records). Download it with `kaggle kernels output ...`.

## Checked before the GPU runs (2026-10-26, CPU smoke test with `trl-internal-testing/tiny-Qwen3ForCausalLM`)

- train_lora → adapter → `run.py --backend transformers --adapter` → `src.eval.tables`: runs end to end.
- Fixed for transformers 5 (Kaggle's version): `warmup_ratio` is gone (warmup now as a step count);
  `apply_chat_template(tokenize=True)` returns a dict (prompt now tokenized from the chat text, as at inference).
- Real Qwen3-8B tokenizer: the training prompt ends exactly like the inference prompt
  (`<|im_start|>assistant\n<think>\n\n</think>\n\n`, thinking off); the loss is only on
  `{"type": "RISK", ...}<|im_end|>`; `<|im_end|>` is an EOS id, so generation stops after the answer.
- 41 of the 1,034 Phase A examples are over 4,096 tokens (37 ATBench UNSAFE, 4 SAFE): dropped and counted in
  `train_stats.json` (Step 16.6).
- T4 memory (no flash attention on a T4): training splits the 4-bit model over both GPUs (one GPU ran out of memory
  on 4k-token examples) and computes logits only for the target positions; evaluation splits the float16 model
  (~16.4 GB) over both and reads prompts over 1,024 tokens into the cache in pieces.
- Invalid answers: the raw text (first 1,000 characters) goes to `invalid_outputs.jsonl` next to `predictions.jsonl`.
- Same library versions for both runs: `PIP` in `base_eval/run_base_eval.py`, versions written to `notes.json`.
  If the first base run used other versions than the fine-tune job, rerun the base job before comparing.

## Data rules

- The code dataset is `git archive HEAD`: committed files only. The push script refuses if `.env`,
  AgentRisk data or model weights would be in it.
- **AgentRisk is never uploaded** (no licence, R14.1): each job downloads it from Hugging Face at the
  pinned revision and converts it inside the job.
- Jobs write only results to `/kaggle/working/results` (ids, gold labels, model output; no record text).
- A fine-tuned adapter goes to a **private** Hugging Face repo: it is trained on AgentRisk, whose licence
  is unknown, so it is not published until the organisers answer.
