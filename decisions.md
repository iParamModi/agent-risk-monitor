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
| 2026-10-19 | Tool-choice check (`compare_tools`) and the table live in `scripts/run_smoke.py`; a task passes if every expected tool was used (extra lookups are fine) | Spec names no module for step 14; expected_tools lists the tools that must appear, not the only ones allowed. |
| 2026-10-19 | `run_smoke.py` table adds `writes_done` and `missing` columns; `main()` returns the rows | Shows at a glance what each `--gate` branch did; lets tests and the live test check results. |
| 2026-10-19 | Run as `python -m lma_agent.scripts.run_smoke` | `lma_agent/scripts/` is a package so imports work without path hacks. |
| 2026-10-19 | Agent model changed from `llama-3.3-70b-versatile` to `openai/gpt-oss-120b` (user decision) | Groq returns 404 `model_not_found` for Llama 3.3 70B on this key, and no Llama chat model is offered. GPT-OSS 120B is the largest tool-calling model available. |
| 2026-10-19 | On 429, wait max(retry-after, 2/4/8 s backoff) instead of trusting retry-after alone | Live run: Groq said wait 1.5 s on an 8,000 tokens/min limit; three short waits were not enough and the episode ended in `error`. |
| 2026-10-25 | Company follows the seed vocabulary: `grant_access`/`revoke_access` -> `grant_permission`/`revoke_permission(user, resource, level read/write/admin)`; file args `path` -> `file`; `share_file(file, with)`; `write_cells(file, cells, content)`; `send_email(to, subject, body?, attachment?)` with one recipient; `transfer_money(amount_inr)`; `get_repo_info` -> `get_repo`; read args `file`/`user`/`account`/`contact` | Team decision: the monitor is trained on the seeds, so the demo company must speak the same language (`docs/alignment_issues.md`). Contract in `scripts/check_seed_vocab.py`; `test_write_tools_match_seed_vocabulary` fails if they drift. |
| 2026-10-25 | Added `move_file`, `edit_file(content?)`, `archive_repository`, `create_event`; removed `set_repo_visibility` (no seed uses it) | The 4 actions the seeds use but the company lacked; `move_file` is needed for the pricing-sheet T2c demo. |
| 2026-10-25 | Folders with inherited sharing: `CompanyState.folders`; `File.sharing = None` inherits the nearest folder; values `internal` / `public` / `external:<org>` (old `none` -> inherit internal, old `external` -> `public` for the public files); added `/Partner_Share` (external:globex) and `/Public` | Seeds model sharing per folder; moving a file into an external folder must change its sharing (stale fact). |
| 2026-10-25 | Seed field names/values: `User.role`, `approval_limit_inr`, `is_external`, `status`; `Contact(contact_id, kind)`; `Account(type, balance_inr)`; `Repo(owner_team, archived)`; `restricted` classification; hidden `attrs: {}` on every entity | Seeds use ~80 hidden facts (`legal_hold`, `kyc_status`, ...); one hidden dict holds them all instead of 80 fields. Read tools never return `attrs`. |
| 2026-10-25 | A `file` arg is a full path or a unique bare name (`ambiguous` error otherwise); `with`/`to`/attendees accept a user id, contact id, email, `team_drive` or `external_link` | In-domain seeds use bare names, OOD seeds full paths; both must run. |
| 2026-10-25 | Tool phases in `configs/tool_phases.yaml` use the seed names (`grant_permission`, `revoke_permission`, `get_repo`; no `set_repo_visibility`); `move_file`, `edit_file`, `archive_repository` are phase 1; `create_event` phase 2 (user decision) | `move_file` drives the T2c stale-fact cases and the pricing-sheet demo; the other two are built and used by 16 seeds. |
| 2026-10-25 | `split_by_phase.py` buckets a whole seed (worst bucket over all subtypes and A/B records); any `OOD-*` seed / `set: ood` record goes to ood test (user decision) | Seeds and pairs never split across phases; OOD reworded seeds use phase 1 tools but must stay test-only. |
