# To Meet: deployment reply (from Prateek, 2026-11-12)

Sorry for the late answer to your 10 Nov check-in.

## 1. Kaggle username

**`prateek99491`**: please share the private dataset **`meet6868/agent-risk-adapter-final`** (the adapter trained on 11 Nov) with this account. The demo will use this adapter, so it matches the final system in the report. I don't need the Phase B one.

The adapter stays private: it is loaded only inside a private Kaggle notebook, and no weights go into the repo.

## 2. What I will finish by 14 Nov

| Part | Status | Plan |
|---|---|---|
| Live gate: `monitor_gate` in `lma_agent/agent/gate.py` calls `run_monitor`; gateway `for_state(state)` answers checks from the live simulator state; event log per run | doing now | tested on CPU with `FakeModel` |
| 3 new demo tasks (never test or OOD records): files visible (0 checks expected), sharing hidden (1 check, `check_file_sharing`), AcmePay `delete_repository` on production (ASK_CONFIRMATION, YES and NO endings) | doing now | `lma_agent/tasks/demo_tasks.yaml` |
| Real recorded runs: Qwen3-8B + final adapter on Kaggle T4 x2, agent `openai/gpt-oss-120b` on Groq, `selective` and `always` | after you share the dataset | `kaggle/demo_record/`, logs in `outputs/live/demo/` |
| Replay website: FastAPI + one static page that replays the recorded runs (no GPU on the server) | 13 Nov | `src/service/` |

## 3. What I am cutting

- **Live runs with 2 agent LLMs (PLAN Step 22)**: cut. No second agent LLM is picked, and there are no `outputs/tables/live.md` results.
- **Live service** (`/v1/check`, `/v1/continue` against a running model): cut. Only clearly marked stubs, off by default.
- **Pricing-sheet demo**: cut unless time is left after the three tasks above.

**For the report:** please claim only a demo of recorded real runs of the final monitor on 3 new tasks, replayed in a web page. Don't claim a live service or live-run results. I'll add the demo results table here once the Kaggle runs are done.
