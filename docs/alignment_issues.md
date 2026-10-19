# Training data vs demo company: what must match

**For:** Prateek (`lma_agent/`) and Param (`data/seeds/`)
**Raised by:** Meet, 2026-10-19
**Status:** open, to be solved by Prateek + Param

## Why this matters

Team plan: **fine-tune the monitor on generated data from Param's seeds**, then **demo and live-run it in Prateek's company** (`lma_agent/`). That is a good plan, and it doubles as a generalization test.

But the monitor learns exact **action names, argument names, check tools and fact values** from training. If the demo company uses different ones, the monitor fails at demo time for the wrong reason. Fixing names now takes about an hour. After records are generated and the model is trained, it means a rebuild and retrain.

## 1. Action names (7 of 12 seed actions are missing in `lma_agent/tools.yaml`)

| Seeds use | # seeds | `lma_agent` has | Decide |
|---|---|---|---|
| `grant_permission` | 28 | `grant_access` | pick one name |
| `revoke_permission` | 2 | `revoke_access` | pick one name |
| `edit_file` | 6 | — | add to lma_agent, or change seeds to `write_cells` |
| `move_file` | 5 | — | add to lma_agent (**needed for the pricing-sheet T2c demo**) |
| `archive_repository` | 5 | `set_repo_visibility` (not the same) | add, or change seeds |
| `create_event` | 4 | — | add to lma_agent, or drop from seeds |
| `transfer_money`, `share_file`, `send_email`, `delete_file`, `delete_repository`, `write_cells` | 101 | same names | ✅ only the args differ (below) |

## 2. Argument names

| Action | Seeds | `lma_agent` |
|---|---|---|
| `delete_file` | `file` | `path` |
| `share_file` | `file`, `to` / `with`, `to_folder` | `path`, `recipient`, `permission` |
| `transfer_money` | `amount_inr`, `from_account`, `to_account` | `amount`, `from_account`, `to_account` |
| `write_cells` | `file`, `cells`, `content` | `path`, `range`, `values` |
| `send_email` | `to`, `subject`, `attachment` | `to` (list), `subject`, `body`, `attachments` |
| `grant_*` | `user`, `resource`, `level` | `user_id`, `resource`, `role` |
| all seed actions | extra `requested_by` | — |

## 3. Company model and fact values

| Thing | Seeds | `lma_agent/sim/models.py` |
|---|---|---|
| file sharing values | `internal` / `external:<org>` / `public` | `none` / `internal` / `external` |
| folders | yes; files **inherit their folder's sharing** (this is what makes T2c stale facts) | no folders |
| classification | public / internal / confidential / **restricted** | no `restricted` |
| approval limit field | `approval_limit_inr` | `approval_limit` |
| other hidden fields | about 50 in `docs/Policy.md` (`locked`, `environment`, `owner_team`, ...) | check which exist |

## 4. Monitor check tools

The monitor is trained to call read-only `check_*` tools (`check_file_sharing`, `check_approval_limit`, ...; full list in `docs/Policy.md`, section A). `lma_agent` has agent tools only. The demo needs a **check gateway** on top of `lma_agent/sim/readers.py`, with the same tool names, arguments and return values as in training.

## 5. Conversation format

`lma_agent` logs episodes as `StepLog`. The monitor reads our record format (`configs/schemas/record.schema.json`: `role`, `text`, `tool_call`, `action_text`). This needs a small converter from `StepLog` to a record trajectory plus `proposed_action`.

## What to produce

1. **One shared list** that both sides follow (PLAN Step 2.5):
   - `configs/tools.yaml`: the canonical action and argument names, plus the monitor's `check_*` tools and their return values.
   - `configs/check_table.yaml`: which checks apply to which action.
2. Rename in the seeds **or** in `lma_agent` to match it. Who changes what is your call.
3. Add folders and folder-inherited sharing to `lma_agent/sim`, or agree the pricing-sheet demo runs only on generated data.
4. Write down the result in `docs/decisions.md` (PLAN Step 2). That is not the same file as the root-level `decisions.md` build log.

## Also tell the team

The agent LLM is now `openai/gpt-oss-120b` on Groq, not Llama 3.3 70B (see `STATUS.md`). It is non-Qwen, so that is fine, but PLAN Step 22 needs **two agent LLMs from different families**. The second one is still to be chosen.
