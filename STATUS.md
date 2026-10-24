# Agent loop — build status
Last updated: 2026-10-19

Spec: `flow_agent.md` (this is `flow.md`; it also stands in for `agent_flow.md`, which was merged into it). Build guide: `INSTRUCTIONS.md`.
Package: `lma_agent/` at the repo root. Tests: `tests/agent/`. Run tests with `.venv/bin/python -m pytest -q`.

| # | Step | Status | Files | Notes |
|---|------|--------|-------|-------|
| 1 | config + skeleton | done | lma_agent/config.py, __init__.py files, requirements.txt, .env.example, .gitignore | `import lma_agent.config` works |
| 2 | sim/models.py | done | lma_agent/sim/models.py, tests/agent/test_models.py | added `exports` and `invalid` tool_type (decisions.md) |
| 3 | sim/seed_state.py | done | lma_agent/sim/seed_state.py, tests/agent/test_seed_state.py | seed 0 = 10 users, 20 files, 5 contacts, 4 accounts, 4 repos, 5 emails, 3 customers |
| 4 | sim/readers.py | done | lma_agent/sim/readers.py, tests/agent/test_readers.py | NotFound is a LookupError; 2 extra helpers |
| 5 | tools.yaml + tools/registry.py | done | lma_agent/tools.yaml, lma_agent/tools/registry.py, tests/agent/test_registry.py | 21 tools: READ 10, WRITE 11 (3 OOD) |
| 6 | tools/validate.py | done | lma_agent/tools/validate.py, tests/agent/test_validate.py | jsonschema Draft 2020-12; catches unknown tool, missing arg, wrong type, extra args |
| 7 | tools/read_tools.py + run_read | done | lma_agent/tools/read_tools.py, tests/agent/test_read_tools.py | hidden-field test runs over every read tool; state hash unchanged |
| 8 | tools/write_tools.py + apply_action | done | lma_agent/tools/write_tools.py, tests/agent/test_write_tools.py | each write tested for exact change + input state untouched |
| 9 | agent/llm.py (live Groq call) | done | lma_agent/agent/llm.py, tests/agent/test_llm.py | live test passes on openai/gpt-oss-120b (Llama 3.3 70B not on Groq; see decisions.md) |
| 10 | prompts, gate, user_sim, logger | done | lma_agent/agent/{prompts,gate,user_sim,logger}.py + tests | unit tests pass |
| 11 | agent/loop.py + FakeLLM tests | done | lma_agent/agent/loop.py, tests/agent/test_loop.py | all 7 required FakeLLM tests + multi-call, LLM failure, OOD schema tests; no Groq calls |
| 12 | smoke tasks + run_smoke.py (real Groq) | done | lma_agent/tasks/{smoke_tasks.yaml,load_tasks.py}, lma_agent/scripts/run_smoke.py, tests/agent/test_{load_tasks,run_smoke}.py | 7/7 tasks reach done with real Groq (--gate allow), 0 tool errors |
| 13 | branch tests (--gate block/ask/escalate) | done | tests/agent/test_run_smoke.py | live: allow/ask 7/7 done with writes; block 7/7 done, 0 writes; escalate 7/7 escalated |
| 14 | tool-choice check vs expected_tools | done | lma_agent/scripts/run_smoke.py (compare_tools) | expected tools used 6/7; miss = smoke_fin_01 skips get_account before transfer_money |

## Differences from flow.md
- `agent_flow.md` does not exist; the user confirmed `flow_agent.md` is the single spec. The 21 phase-1 tools are taken from its sections 4.6 and 4.7.
- The repo already has stub modules for the same ideas (`src/env/`, `src/gateway/`, `src/live/agent_runner.py`, `configs/tools.yaml`). They are one-line placeholders, so `lma_agent/` was built as a separate package and they were left untouched.
- See `decisions.md` for every naming/signature change.

## Live run results (2026-10-19, openai/gpt-oss-120b on Groq)
| Gate | Result |
|---|---|
| allow | 7/7 `done`, 0 tool errors, every write correct (deleted exactly report_7 + report_8) |
| ask (user confirms) | 7/7 `done`, writes applied |
| block | 7/7 `done`, 0 writes executed |
| escalate | 7/7 `escalated` after the first write |

Tool choice: expected tools used in 6/7 tasks (1 call per task except file cleanup). The model rarely looks things up before writing: it paid without `get_account` and guessed the pricing sheet path without listing `/finance`. No bad JSON, wrong tools or loops seen.
After a BLOCK it tries workarounds with other writes (e.g. granting `u_riya` admin on AcmePay so it can delete it, emailing an admin), all blocked. Useful cases for the monitor.
Rate limit: this Groq key allows 8,000 tokens/min for gpt-oss-120b, and each request is about 2,000 tokens (mostly tool schemas), so roughly 4 requests per minute.

## Open questions for the user
- Llama 3.3 70B isn't available on Groq for this key, so the agent now uses `openai/gpt-oss-120b` (your choice). Tell the team, since PLAN/DATASET may name Llama.
- The 8,000 tokens/min limit will slow the 40 live tasks; a paid Groq tier or shorter tool descriptions would help.

## Phase split — record format (2026-10-25)
- Tool lists per phase: `configs/tool_phases.yaml`. Phase 1 = 9 read + 11 write in-domain tools (the agent gets these 20; OOD CUST tools only on CUST tasks); phase 2 adds 3 read + 11 write; 12 tools dropped. `lma_agent/tools.yaml` `phase` agrees (`create_event` is phase 2); a test checks it.
- Records (`configs/schemas/record.schema.json`): action tool = `visible.proposed_action.name`; trajectory tools = `visible.trajectory[*].tool_call.name`; `split` (train/val/test, null until split); `seed_id`; `set` (in_domain/ood/external); `source` (ours/r_judge/atbench).
- `data/records/` is still empty (Step 9 not run), so `scripts/split_by_phase.py` splits the **seeds** now (`data/training/seed_phases.json`) and writes `phase{1,2}_{train,val,test}.jsonl`, `ood_test.jsonl`, `rejected.jsonl`, `split_summary.json` once records exist.
- Seeds today: phase 1 **146** (all in-domain except the 4 `create_event` seeds), phase 2 **4**, ood **39**, rejected **6** (OOD-ACC seeds still use `grant_access`; they become ood after Param's seed cleanup).
- Phase 1 write tools by seed count: grant_permission 28, transfer_money 25, share_file 19, send_email 18, delete_file 15, delete_repository 15, write_cells 8, edit_file 6, archive_repository 5, move_file 5 (+ T2c later writes), **revoke_permission 2 (under 5)**.
