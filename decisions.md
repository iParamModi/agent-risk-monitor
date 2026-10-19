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
