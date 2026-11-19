# Selective Environment Verification for Agent-Risk Monitoring

LMA Group Project 2026 — Meet Ghelani, Moiesha, Param Modi, Prateek Tiwari.

A safety monitor for tool-using LLM agents. For each proposed action it reads the
conversation, the action and the most relevant retrieved policies. If a deciding fact is
missing it asks a read-only check tool for just that fact, then returns one of
ALLOW / ASK_CONFIRMATION / BLOCK / ESCALATE. Main question: is checking only when
needed almost as safe as always checking, with far fewer checks?

## Docs

- `docs/Project-Proposal.pdf` — the project proposal
- `docs/reports/OUTPUT.md` — consolidated results: all metrics, hypotheses, error analysis, retrieval ablation
- `docs/DATASET.md` — data sources, cleaning, labels
- `docs/decisions.md` — design-decisions log
- `docs/reports/final_results_v2.md` — final result tables
- `report/final_submission.pdf` — the final paper

## Models and data

Private Hugging Face repo **`meet5568/Agent-Risk`** (one root, with a model card and a data card):

- `phaseA/` — LoRA adapter for Qwen3-8B, collected data only (risk label + type)
- `phaseB_v1/` — adapter of the mid report (28 Oct, our first 248 train records)
- `phaseB_v2/` — **final adapter** (11 Nov, used by system v1 and system v2 in the final report)
- `data/` — our 594 records, seeds, policies, check tools, prompts, collected split lists (IDs only)
- `results/` — result tables and the predictions + traces of the final runs

The adapters are trained partly on AgentRisk (no licence): keep the repo private.

## Setup

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in keys, never commit
make external          # download R-Judge + ATBench into data/raw/
make test
```

`data/generated/`, `models/` and `outputs/runs/` are not in git.
`data/raw/` (R-Judge + ATBench) is in git. R-Judge has no licence file, so keep this repo private.
