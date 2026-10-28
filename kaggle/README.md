# Kaggle jobs (GPU)

We have no GPU, so model runs go to Kaggle (free GPU T4 x2, 2 x 16 GB). Everything stays **private**.

| Job | Folder | What |
|---|---|---|
| 1. Base model on external val (no training) | `kaggle/base_eval/` | Qwen3-8B (float16, rev `b968826`), 241 external val records, scored with `src.eval.tables` |
| 2. Fine-tune, then the same val | `kaggle/finetune/` | QLoRA (R13.1: r 16, alpha 32, lr 2e-4, 2 epochs, 4-bit NF4) on `phase_a_train.txt` (1,034), then the same 241 val records with the adapter (float16 base + LoRA) |
| 2b. Saved adapter on the same val | `kaggle/lora_eval/` | the evaluation part of job 2 only, on an adapter uploaded as the PRIVATE dataset `meet6868/agent-risk-adapter` (a failed run's output cannot be a Kaggle input); for when training finished but evaluation did not |

Run 1 first, then 2 (Meet): comparing the two tables shows what training adds. Same records, code and precision.

**Phase B** (our records + the external ones, PLAN Step 16): `python -m src.training.build_sft --phase b` builds
(a) first-pass + (b) second-pass examples from `data/records/train.jsonl` (phase 1 tools) plus the same (c). It
stops and writes nothing until every check-needed record has `gold.required_checks` (seed_to_record.md D4) and the
check gateway exists (`src/gateway/gateway.py: for_record`); then job 2 runs with `--phase b`.

## Our records in 4 settings (`kaggle/our_eval/`) and talking to the model

`kaggle kernels push -p kaggle/our_eval --accelerator NvidiaTeslaT4`: our 40 val records, base and Phase B adapter, each
in 2 policy conditions (gold + 2 look-alikes; real top-3 retrieval) x 4 settings, one model load per model. Download
with `kaggle kernels output meet6868/agent-risk-our-eval -p outputs/kaggle/our_eval`, then read what the model did:
`python scripts/show_traces.py outputs/kaggle/our_eval/results/runs/ours_phase_b_gold_selective [--wrong] [--prompt]`.

Talk to the model yourself (needs the GPU): new Kaggle notebook, accelerator GPU T4 x2, internet on, add the datasets
`meet6868/agent-risk-code` and `meet6868/agent-risk-adapter-phase-b`, then:
```python
import glob, shutil, sys, subprocess
src = glob.glob("/kaggle/input/**/src/monitor/run.py", recursive=True)[0].rsplit("/src/", 1)[0]
shutil.copytree(src, "/tmp/repo", dirs_exist_ok=True); sys.path.insert(0, "/tmp/repo")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "peft", "sentence-transformers", "rank-bm25", "jsonschema"])
subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "-q", "torchao"])
from scripts.chat_monitor import Chat
adapter = glob.glob("/kaggle/input/**/adapter_config.json", recursive=True)[0].rsplit("/", 1)[0]
chat = Chat(adapter=adapter)                       # Chat(adapter=None) for the base model
chat.record("IND-FIN-T1-001-B")                     # replay a val/train record, selective, gold policies
chat.ask("Send 3,50,000 from acct_12 to acct_77.", {"name": "transfer_money", "args": {"from_account": "acct_12",
         "to_account": "acct_77", "amount_inr": 350000}}, world="IND-FIN-T1-001-B")   # your own request
```

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
