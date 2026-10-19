# Agent loop — decisions

Changes from `flow_agent.md` (the `flow.md` spec) and small choices made while building `lma_agent/`.

| Date | What | Why |
|---|---|---|
| 2026-10-19 | `flow_agent.md` is used as both `flow.md` and `agent_flow.md` | The user renamed `flow.md`; `agent_flow.md` was never added. Tool list taken from sections 4.6/4.7. |
| 2026-10-19 | Code in `lma_agent/`, tests in `tests/agent/` (not `lma_agent/tests/`) | INSTRUCTIONS ground rule 2 puts tests at the root; a subfolder keeps them apart from the existing `src/` tests. |
| 2026-10-19 | Local env is `.venv` with Python 3.12 and only the agent packages | System Python is 3.14 with no packages; the full `requirements.txt` pulls in vllm/torch, which the loop doesn't need. |
| 2026-10-19 | `config.RUNS_DIR` = `<repo>/runs` | Single place for episode files; `runs/` is gitignored. |
| 2026-10-19 | Live tests are marked `@pytest.mark.live` and skipped unless `LMA_LIVE=1` | Keeps `pytest -q` free of API calls. |
| 2026-10-19 | `CompanyState.exports: list[dict] = []` added | `export_customer_data` "logs an export"; the spec state had nowhere to log it. |
| 2026-10-19 | `StepLog.tool_type` also allows `"invalid"` | `handle_call` in section 4.13 logs a failed validation with type `"invalid"`, which the section 3 Literal didn't allow. |
| 2026-10-19 | Seed 0 is fixed; other seeds only jitter filler file dates and two balances | Smoke tasks and demos rely on exact seed-0 values; seeds still give distinct, repeatable states. |
| 2026-10-19 | `apply_overrides`: a key with no dot sets a top-level field; an unknown item key adds a new item; field paths can go into dicts (`content.B4`) | Lets tasks set `current_user`, add files, and change single spreadsheet cells. |
| 2026-10-19 | Added helpers `_is_internal_email` and `_resource_exists` to `readers.py` | Needed by `share_file` (external check) and `grant_access`/`list_permissions` (does the resource exist). |
| 2026-10-19 | `tools.yaml` lives in `lma_agent/`; OOD tools carry `ood: true` (domain `CUST`) | `get_agent_tool_schemas(include_ood=...)` filters on that flag. The old `configs/tools.yaml` stub is left alone. |
| 2026-10-19 | Arg schemas set `additionalProperties: false`; `read_inbox.n` optional (default 5) | Unknown/garbled args (`_raw`) fail validation; Llama often omits `n`. |
| 2026-10-19 | `write_cells.values` is a flat list filled row by row; `send_email.to` is a list | Simple shape that maps cleanly onto `Email.to` and single cells. |
| 2026-10-19 | `list_files` includes subfolders and returns `not_found` for an empty/unknown folder; `list_permissions` returns `roles: {}` for an existing resource with no roles; `read_inbox` is newest first | Clearer feedback for the agent. |
