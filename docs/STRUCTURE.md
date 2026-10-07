# STRUCTURE.md — Where Every File Lives

This file shows the folder layout of the project repository, what goes in each folder, how files are named, and the rules for storing them. If you are not sure where something goes, check here first.

Related files: `PLAN.md` (the work steps) and `DATASET.md` (data details).

---

## 1. Full folder tree

```
agentrisk-monitor/
├── README.md                      # what the project is, how to install, how to run
├── requirements.txt               # pinned package versions
├── Makefile                       # short commands (make data, make train, ...)
├── .env.example                   # names of the API keys we need (no real keys)
├── .gitignore
│
├── docs/
│   ├── PLAN.md                    # step-by-step work plan
│   ├── STRUCTURE.md               # this file
│   ├── DATASET.md                 # data sources, cleaning, labels
│   ├── decisions.md               # LOCKED definitions (PLAN Step 2) + changelog
│   └── labeling_guide.md          # guide for the human annotators (PLAN Step 10)
│
├── configs/
│   ├── decisions.yaml             # 4 decisions, precedence order, ranks for metrics
│   ├── risk_types.yaml            # risk_label, risk_type (+ NONE), risk_cause lists
│   ├── check_table.yaml           # action type -> ALL checks that apply ("always check")
│   ├── tools.yaml                 # read-only check tools + argument schemas (shown to the model)
│   ├── write_actions.yaml         # agent write actions (the monitor may never call these)
│   ├── retrieval.yaml             # embedding model, BM25 weight, top_k = 3
│   ├── schemas/
│   │   ├── monitor_pass1.schema.json   # DECISION or NEED_INFORMATION
│   │   ├── monitor_pass2.schema.json   # DECISION only
│   │   ├── monitor_risk.schema.json    # RISK (external trajectories)
│   │   ├── record.schema.json          # one data record (DATASET.md, section 4)
│   │   └── seed.schema.json            # one seed spec (DATASET.md, section 3.4)
│   ├── models/
│   │   ├── qwen3_8b_base.yaml
│   │   ├── qwen3_8b_lora.yaml
│   │   └── qwen3_235b_api.yaml
│   ├── train/
│   │   └── lora_v1.yaml           # QLoRA settings (PLAN Step 17)
│   └── experiments/
│       ├── main.yaml              # models x settings grid
│       ├── ablations.yaml
│       ├── ood.yaml
│       └── live.yaml
│
├── data/
│   ├── raw/                       # downloads exactly as received. In git (repo must stay private).
│   │   ├── r_judge/               # cloned GitHub data (27 JSON files) + VERSION.txt
│   │   └── atbench/               # ATBench/test.json from Hugging Face + VERSION.txt
│   ├── external/                  # R-Judge + ATBench in OUR record format
│   │   ├── r_judge.jsonl
│   │   ├── atbench.jsonl
│   │   ├── risk_type_map.yaml     # ATBench harm -> our risk_type
│   │   ├── risk_type_review.csv   # R-Judge: LLM suggestion + human final choice
│   │   └── splits/
│   │       ├── r_judge_train.txt  # one record_id per line
│   │       ├── r_judge_val.txt
│   │       ├── r_judge_test.txt
│   │       ├── r_judge_train_sample300.txt
│   │       ├── atbench_train.txt
│   │       ├── atbench_val.txt
│   │       ├── atbench_test.txt
│   │       └── atbench_train_sample300.txt
│   ├── policies/
│   │   ├── policies.jsonl         # VISIBLE policy text. The only policy file used in prompts.
│   │   ├── policies_ood.jsonl     # reworded policies for the OOD test
│   │   ├── policy_logic.yaml      # HIDDEN machine logic for gold labels. NEVER in prompts.
│   │   └── conflicts.yaml         # conflict pairs used for T5
│   ├── seeds/
│   │   ├── allocation.csv         # domain x case-type counts
│   │   ├── in_domain/             # 150 files, e.g. IND-PRIV-T2-014.yaml
│   │   └── ood/                   # 45 files, e.g. OOD-CUST-T1-003.yaml
│   ├── generated/                 # in-between files. Can always be rebuilt. NOT in git.
│   │   ├── skeletons/             # conversation skeletons made by code
│   │   ├── drafts/                # writer-LLM text before merging
│   │   └── reports/               # automatic-check, leakage and duplicate reports
│   ├── records/                   # FINAL records
│   │   ├── all_in_domain.jsonl    # before splitting
│   │   ├── all_ood.jsonl
│   │   ├── train.jsonl
│   │   ├── val.jsonl
│   │   ├── test.jsonl             # LOCKED
│   │   ├── ood_test.jsonl         # LOCKED
│   │   └── splits.yaml            # seed_id -> split
│   ├── labels/                    # human labels (PLAN Step 10)
│   │   ├── kappa_items.csv        # the 100 items to label
│   │   ├── annotator_a.csv
│   │   ├── annotator_b.csv
│   │   ├── kappa_report.json
│   │   └── disagreement_notes.md
│   ├── training/
│   │   ├── sft_train.jsonl
│   │   ├── sft_val.jsonl
│   │   └── stats.json             # counts per example kind, dropped long examples
│   └── LOCKED_TEST.sha256         # hashes of test.jsonl and ood_test.jsonl
│
├── prompts/
│   ├── monitor_v1.txt             # monitor prompt (new versions = new files)
│   ├── writer_conversation_v1.txt # writer-LLM prompt for data generation
│   └── risk_type_suggest_v1.txt   # LLM prompt for R-Judge risk-type suggestions
│
├── src/
│   ├── common/                    # set_seed, JSONL read/write, ID helpers, logging
│   ├── env/                       # the simulated company
│   │   ├── entities.py            # users, folders, files, repos, accounts, contacts, events, records
│   │   ├── actions.py             # agent write actions + agent read tools (get_file_info, ...) + apply_action
│   │   ├── names.py               # neutral names, random timestamps, rupee amounts
│   │   └── loader.py              # builds a start state from a seed spec
│   ├── gateway/
│   │   ├── read_tools.py          # check_* tools
│   │   ├── gateway.py             # validation, retry, write guard, counting
│   │   └── audit.py               # one JSON line per call
│   ├── policies/
│   │   ├── store.py               # loads policies.jsonl
│   │   ├── retriever.py           # embeddings + BM25, top-3
│   │   ├── trust_rule.py          # is_fact_known(...)  (shared by labeler + analysis)
│   │   └── gold_engine.py         # HIDDEN logic -> gold decision. Never used by baselines.
│   ├── data_gen/
│   │   ├── skeleton.py            # builds conversation skeletons with real tool results
│   │   ├── writer_llm.py          # calls the writer LLM, keeps placeholders intact
│   │   ├── variants.py            # T1 A/B, T2 a-d, T3-T5 v1/v2
│   │   ├── labeler.py             # gold fields from gold_engine + trust_rule
│   │   ├── auto_checks.py         # all automatic checks (DATASET.md, section 3.8)
│   │   ├── leakage_check.py       # A/B identity script
│   │   ├── dedup.py               # near-duplicate check across splits
│   │   └── split.py               # split by seed, write hashes
│   ├── external/
│   │   ├── load_rjudge.py
│   │   ├── load_atbench.py
│   │   ├── normalize.py           # into our record format
│   │   ├── map_risk.py            # risk-type mapping + LLM suggestions
│   │   └── sample.py              # 70/10/20 split + balanced 300 sample
│   ├── monitor/
│   │   ├── prompt_builder.py      # reads ONLY visible fields + policies.jsonl
│   │   ├── parser.py              # strict JSON parsing against the schemas
│   │   ├── loop.py                # run_monitor(record, setting, model)
│   │   └── settings.py            # never / always / selective / oracle
│   ├── baselines/
│   │   ├── rules_only.py          # never check
│   │   └── rules_env.py           # always check
│   ├── training/
│   │   ├── build_sft.py           # makes sft_train.jsonl / sft_val.jsonl
│   │   └── train_lora.py          # QLoRA training
│   ├── eval/
│   │   ├── metrics.py
│   │   ├── bootstrap.py           # resampling by seed
│   │   ├── stats_tests.py         # Wilcoxon, McNemar, hypothesis check
│   │   ├── run_eval.py
│   │   ├── error_analysis.py
│   │   └── tables.py              # writes outputs/tables/*.md
│   ├── service/
│   │   ├── app.py                 # FastAPI: /v1/check, /v1/continue, /health
│   │   └── schemas.py
│   ├── live/
│   │   ├── agent_runner.py        # runs an agent LLM inside the simulator
│   │   ├── scripted_user.py       # answers YES/NO to confirmation questions
│   │   ├── tasks/                 # 30-50 live task scripts (YAML)
│   │   └── live_eval.py
│   └── demo/
│       ├── acmepay_demo.py
│       └── pricing_sheet_demo.py
│
├── scripts/                       # one command per big job
│   ├── download_external.sh
│   ├── build_dataset.sh
│   ├── train_lora.sh
│   ├── run_main.sh
│   ├── run_ablations.sh
│   ├── run_ood.sh
│   ├── run_live.sh
│   └── serve.sh
│
├── models/                        # LoRA adapters. NOT in git (shared drive or private HF repo).
│   └── lora_qwen3_8b_v1/
│
├── outputs/
│   ├── runs/<run_id>/             # one folder per run, never overwritten
│   │   ├── config.yaml            # exact settings + commit hash
│   │   ├── predictions.jsonl      # one line per record
│   │   ├── gateway_audit.jsonl    # every check call
│   │   ├── metrics.json
│   │   └── log.txt
│   ├── retrieval/                 # recall@3 reports
│   ├── live/                      # live-run logs
│   ├── service_logs/
│   ├── tables/                    # main.md, ablations.md, ood.md, live.md, errors.md
│   ├── figures/
│   └── results_sheet.csv          # one row per run
│
├── tests/
│   ├── test_env.py
│   ├── test_gateway.py
│   ├── test_trust_rule.py
│   ├── test_leakage.py
│   ├── test_prompt_has_no_hidden_fields.py
│   ├── test_parser.py
│   ├── test_metrics.py
│   └── test_locked_test_set.py    # fails if test files change
│
└── report/                        # final report source + figures
```

---

## 2. What each top-level folder is for

- **docs/** — documents people read: the plan, this file, the dataset guide, the locked decisions, and the labeling guide.
- **configs/** — every setting lives here, not inside code. To change a setting, change a config file, never the code.
- **data/** — all data, from raw downloads to final records. Data moves in one direction only: raw → external or generated → records → training.
- **prompts/** — every prompt as a plain text file. Old versions are kept so results can be repeated.
- **src/** — all Python code, one folder per part of the system.
- **scripts/** — short shell scripts that run a whole job with one command.
- **models/** — trained adapters (big files, kept outside git).
- **outputs/** — everything produced by runs: predictions, logs, metrics and tables.
- **tests/** — automatic tests. Run `make test` before every merge.
- **report/** — the final report.

## 3. How data flows through the folders

```
data/raw/  ──normalize──▶  data/external/  ──split + sample──▶  data/external/splits/
                                                                        │
data/seeds/ ─▶ data/generated/ (skeleton → draft → checks) ─▶ data/records/ ─▶ data/training/
                                                                        │              │
                                                                        ▼              ▼
                                                  src/monitor + model ─▶ outputs/runs/ ─▶ outputs/tables/ ─▶ report/
```

## 4. Naming rules

**Domain codes** (used in seed IDs and policy IDs):
- `FILE` — file deletion
- `PRIV` — privacy / sharing
- `ACC` — access control
- `FIN` — money transfers
- `REPO` — repositories / security
- `CAL` — calendar / email
- `CUST` — customer data (OOD only)

**Seed ID:** `<SET>-<DOMAIN>-<TYPE>-<NNN>`
- Example: `IND-PRIV-T2-014` (in-domain, privacy domain, case type T2, seed number 14).
- `SET` is `IND` (in-domain) or `OOD`.

**Record ID:** the seed ID plus a suffix.
- T1 hidden-state pairs: `-A` and `-B`. Example: `IND-FIN-T1-003-A`
- T2 subtypes: `-a`, `-b`, `-c`, `-d`. Example: `IND-PRIV-T2-014-c`
- T3, T4, T5 versions: `-v1`, `-v2`. Example: `IND-ACC-T5-009-v2`

**External record ID:**
- R-Judge: `RJ-<file>-<id>`, for example `RJ-mail-38`.
- ATBench: `ATB-<id>`, for example `ATB-512`.

**Policy ID:** `P_<DOMAIN>_<NN>`, for example `P_FIN_01`. OOD rewordings keep the same number with `_R`, for example `P_FIN_01_R`.

**Run ID:** `<yyyymmdd>_<model>_<setting>_<split>_<commit7>`
- Example: `20261020_lora8b_selective_test_a1b2c3d`.
- Model names: `rules`, `base8b`, `lora8b`, `q235b`.
- Settings: `never`, `always`, `selective`, `oracle`.

**Prompt and config versions:** add `_v1`, `_v2`, and so on. Never edit an old version that a run has already used. Make a new file instead.

## 5. File formats

- **JSONL** (one JSON object per line) for records, predictions, audit logs and training files. Easy to stream and append.
- **YAML** for configs and seed specs, because people edit these by hand.
- **CSV** for human labels and the results sheet, so they open in a spreadsheet.
- **JSON** for metrics and reports from code.
- **Markdown** for docs and results tables.
- **Text encoding:** UTF-8 everywhere. JSON keys in snake_case.

## 6. Storage rules

1. **`data/raw/` is read-only.** Never edit a download. Write the source URL and version hash in `VERSION.txt`.
2. **Hidden information never reaches a prompt.** `prompt_builder.py` reads only the `visible` part of a record and `policies.jsonl`. The test `test_prompt_has_no_hidden_fields.py` fails if a prompt contains hidden state, gold fields, or text from `policy_logic.yaml`.
3. **Locked test files.** `test.jsonl` and `ood_test.jsonl` are hashed in `LOCKED_TEST.sha256`. `test_locked_test_set.py` fails if they change.
4. **Runs are never overwritten.** Each run gets a new `run_id` folder with its config and commit hash.
5. **What stays out of git** (listed in `.gitignore`): `data/generated/`, `models/`, `outputs/runs/`, `outputs/service_logs/`, `.env`. Share these through the team drive.
6. **What goes in git:** code, configs, prompts, seeds, policies, final records, labels, `outputs/tables/`, `results_sheet.csv`, docs and report.
7. **R-Judge raw files are committed, so this repository must stay private.** R-Judge has no licence file: research use only, never make the repo public or share the raw files outside the team, and cite the paper. If the repo ever goes public, remove `data/raw/r_judge/` from git history first.
8. **Secrets only in `.env`.** Never paste a key into code, configs or notebooks.
9. **Labels are fixed through code, not by hand.** If a gold label is wrong, fix the rule in `policy_logic.yaml` or the generator, then rebuild. This keeps labels reproducible.

## 7. Who owns which folders

The owner reviews every change to their folders.

- **M1 — Data:** `data/` (M3 co-reviews `data/policies/`), `src/data_gen/`, `src/external/`, `docs/labeling_guide.md`
- **M2 — Environment:** `src/env/`, `src/gateway/`, `src/service/`, `src/live/`, `configs/tools.yaml`, `configs/write_actions.yaml`, `configs/check_table.yaml`
- **M3 — Model:** `src/policies/retriever.py`, `src/monitor/`, `src/training/`, `prompts/`, `configs/models/`, `configs/train/`, `models/`
- **M4 — Experiments:** `src/eval/`, `src/baselines/`, `src/demo/`, `configs/experiments/`, `outputs/tables/`, `results_sheet.csv`
- **Everyone:** `docs/decisions.md` (changes need all four), `report/`

## 8. Makefile commands

- `make test` — run all tests.
- `make external` — download R-Judge and ATBench, normalize them, split and sample.
- `make data` — seeds → skeletons → writer LLM → variants → labels → checks → records.
- `make split` — split by seed and write the test hashes.
- `make train` — build the SFT files and train the LoRA adapter.
- `make eval-val` — run the experiment grid on validation.
- `make eval-test` — run the final grid on test, OOD and the external test parts.
- `make live` — run live agent tasks.
- `make serve` — start the plug-in service.
- `make tables` — rebuild all tables in `outputs/tables/`.

## 9. `.gitignore` (starting version)

```
.env
__pycache__/
*.pyc
.ipynb_checkpoints/
data/generated/
models/
outputs/runs/
outputs/live/
outputs/service_logs/
wandb/
```
