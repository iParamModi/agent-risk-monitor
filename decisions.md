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
| 2026-10-19 | Write tools mutate the copy `apply_action` gives them; errors (`not_found`, `insufficient_funds`, `values_mismatch`, `no_such_role`, ...) come back as `{"error": ...}` with the original state | One place does the deep copy; failed writes never half-change the state. |
| 2026-10-19 | `share_file` accepts a user id as recipient, stores the email in `shared_with`; permission is only echoed in the result | `File` has no per-recipient permission field. |
| 2026-10-19 | `delete_repository` also drops the repo's roles; `send_email` attachments must be existing files | Keeps the state consistent. |
| 2026-10-19 | `make_client()` sets `max_retries=0` | `call_llm` owns the retry policy (retry-after, else 2/4/8 s, up to `MAX_RETRIES`); SDK retries would double it. |
| 2026-10-19 | `call_llm` also retries Groq's `tool_use_failed` 400 (broken tool-call JSON) and drops `parallel_tool_calls` once if the API rejects it | INSTRUCTIONS step 9. |
| 2026-10-19 | `FakeLLM` lives in `agent/llm.py`; `call_llm` hands off to it when it's passed as the client | One seam for tests, and `run_agent`'s signature stays as in the spec. |
| 2026-10-19 | `assistant_msg()` builds `AssistantMsg.raw` as a clean assistant dict (role, content, tool_calls) | `raw` is appended to `messages` and sent back to Groq, so it must be a valid API message. |
| 2026-10-19 | Installed openai SDK is 3.35 (uses `httpx2`); tests fake the HTTP response object instead of importing httpx | Keeps tests independent of the SDK's HTTP library. |
| 2026-10-19 | System prompt fills `{current_user}` as "Name (user_id, email)" | The agent needs the id/email to act for the user; text otherwise as in section 4.8. |
| 2026-10-19 | `logger.new_episode_id(task_id)` = `<task_id>_<YYYYmmdd-HHMMSS>_<4 hex>`; `fake_gate` takes optional `policy_id`/`reason` | Unique, sortable episode files; BLOCK results show a policy id in tests. |
| 2026-10-19 | `handle_call` takes extra `episode_id` and `step` keyword args (default `""`/`0`) | `make_step_log` needs them (section 4.12) but section 4.13's signature didn't pass them. |
| 2026-10-19 | `run_agent` takes `out_dir=None`; it calls `save_episode` only when given | The call graph saves inside `run_agent`; unit tests shouldn't write to `runs/`. `run_smoke.py` passes `RUNS_DIR`. |
| 2026-10-19 | An exception from `call_llm` ends the episode with status `error` | `EpisodeResult.status` already allows `error`; the section 4.13 sketch had no path to it. |
| 2026-10-19 | A gate-approved write that fails (e.g. `not_found`) is logged with `executed=False` | The state didn't change, so "executed" would be misleading for the monitor's labels. |
