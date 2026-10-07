# Selective Environment Verification for Agent-Risk Monitoring

LMA Group Project 2026 — Meet Ghelani, Moiesha, Param Modi, Prateek Tiwari.

A safety monitor for tool-using LLM agents. For each proposed action it reads the
conversation, the action and the top-3 retrieved policies. If a deciding fact is
missing it asks a read-only check tool for just that fact, then returns one of
ALLOW / ASK_CONFIRMATION / BLOCK / ESCALATE. Main question: is checking only when
needed almost as safe as always checking, with far fewer checks?

## Docs

- `docs/Catalysts.pdf` — the proposal
- `docs/How_Our_Project_Works.pdf` — plain-language guide
- `docs/PLAN.md` — step-by-step work plan
- `docs/STRUCTURE.md` — where every file lives
- `docs/DATASET.md` — data sources, cleaning, labels

## Setup

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in keys, never commit
make external          # download R-Judge + ATBench into data/raw/
make test
```

`data/raw/`, `data/generated/`, `models/` and `outputs/runs/` are not in git.
R-Judge has no licence file: never commit its raw files.
