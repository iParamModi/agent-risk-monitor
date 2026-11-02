# To Prateek: deployment part for the final submission (from Meet, 2026-11-02)

Meet is giving you the whole deployment part: **demo, service and live runs**. All three are one-line stubs today (`src/demo/`, `src/service/`, `src/live/`). Final submission is **14 Nov**.

## Your tasks, most important first

| # | Task | PLAN | By | Done when |
|---|---|---|---|---|
| 1 | Demo: AcmePay and the pricing-sheet stale fact | Step 24 | 8 Nov | Both run from one command, with the audit log and both YES and NO endings; a short screen recording as a backup |
| 2 | Service: `/v1/check`, `/v1/continue`, `/health` | Step 21 | 10 Nov | A test client gets a correct decision in `auto` and `ask` modes |
| 3 | Live runs: 30-50 tasks with 2 agent LLMs | Step 22 | 12 Nov | `outputs/live/` and `outputs/tables/live.md` |

If time runs short, **cut from the bottom**: live runs first, then the service. The demo matters most because it is what people see. The mid report promises none of these as finished ("if time allows"), so the final report should claim only what actually ran.

## Things you need to know

**No GPU on our machines.** The model needs a GPU, so:
- Build and test everything against `FakeModel` first (`src/monitor/models.py`).
- For real runs, load `TransformersModel` on Kaggle (T4 x2), as in `kaggle/README.md` ("Talk to the model yourself"). `OpenAICompatModel` works if you have an endpoint.

**The adapter is private.**
- Use the Phase B adapter now. The final one comes after my retrain on 8-9 Nov, so make the path a setting.
- It is trained on AgentRisk data, which has no licence. **It must never go to a public repo or dataset.** Send me your Kaggle username and I will share the private dataset `meet6868/agent-risk-adapter-phase-b` with you.

**Reuse what exists.**
- Monitor: `run_monitor` in `src/monitor/loop.py`, inputs as in `src/monitor/case_inputs.py`.
- Checks on a live company state: `call_check` in `src/gateway/gateway.py`.
- Agent: `lma_agent/agent/gate.py` is where the monitor plugs in.

**Live runs.**
- Agent 1 is `openai/gpt-oss-120b` on Groq. Agent 2 is still not picked (R13.2): it must be another family and not Qwen. Please pick it and add a Changelog row.
- Groq's limit of 8,000 tokens/min allows about 4 requests per minute, so 40 tasks will take hours. Start early.
- Tasks need fresh states, not train states.

## ⚠️ Be careful

- The gold labeler (`policy_logic.yaml`) may only score live runs, as the rule checker. The monitor must never read it or `hidden`. Keep `tests/test_gateway_no_bypass.py` passing.
- Never commit `.env`, keys or adapter weights.
- Param adds the phase-2 tools to `lma_agent`, and will ask you to review those changes.
