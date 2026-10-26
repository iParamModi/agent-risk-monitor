# Kaggle jobs (GPU)

We have no GPU, so model runs go to Kaggle (free GPU T4 x2, 2 x 16 GB). Everything stays **private**.

| Job | Folder | What |
|---|---|---|
| Base model on external val | `kaggle/base_eval/` | Qwen3-8B (float16, rev `b968826`), 241 external val records, scored with `src.eval.tables` |

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
```

## Data rules

- The code dataset is `git archive HEAD`: committed files only. The push script refuses if `.env`,
  AgentRisk data or model weights would be in it.
- **AgentRisk is never uploaded** (no licence, R14.1): each job downloads it from Hugging Face at the
  pinned revision and converts it inside the job.
- Jobs write only results to `/kaggle/working/results` (ids, gold labels, model output; no record text).
- A fine-tuned adapter goes to a **private** Hugging Face repo: it is trained on AgentRisk, whose licence
  is unknown, so it is not published until the organisers answer.
