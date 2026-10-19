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
| 9 | agent/llm.py (live Groq call) | blocked: no key | lma_agent/agent/llm.py, tests/agent/test_llm.py | code + 9 offline tests done (retry, parse, FakeLLM); live test `LMA_LIVE=1` needs GROQ_API_KEY in .env |
| 10 | prompts, gate, user_sim, logger | done | lma_agent/agent/{prompts,gate,user_sim,logger}.py + tests | unit tests pass |
| 11 | agent/loop.py + FakeLLM tests | missing | | |
| 12 | smoke tasks + run_smoke.py (real Groq) | missing | | |
| 13 | branch tests (--gate block/ask/escalate) | missing | | |
| 14 | tool-choice check vs expected_tools | missing | | |

## Differences from flow.md
- `agent_flow.md` does not exist; the user confirmed `flow_agent.md` is the single spec. The 21 phase-1 tools are taken from its sections 4.6 and 4.7.
- The repo already has stub modules for the same ideas (`src/env/`, `src/gateway/`, `src/live/agent_runner.py`, `configs/tools.yaml`). They are one-line placeholders, so `lma_agent/` was built as a separate package and they were left untouched.
- See `decisions.md` for every naming/signature change.

## Open questions for the user
- No `GROQ_API_KEY` in the environment and no `.env` file, so live steps (9, 12–14) can't run yet.
