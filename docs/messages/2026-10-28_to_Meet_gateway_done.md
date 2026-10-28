# To Meet: the check gateway is done. Rerun the always setting; no retraining

**Why:** the gateway (HIGH PRIORITY #2) is finished, and the always-setting check table is fixed (#7). Only the
always setting changed. Your Phase B adapter and its training file are still valid.

## What the gateway has now

| Part | What it does | Where |
|---|---|---|
| `for_record(record).call(tool, args)` | One gateway per record and setting. Errors are data (`unknown_tool`, `invalid_args`, `not_found`, `write_not_allowed`). Every call counts; selective allows at most 4 | `src/gateway/gateway.py` (part 1, you already use it) |
| `table_calls(action, user)` | The always setting's checks for an action. **New:** it skips `check_file_sharing` when grant_permission's `resource` is a system (`prod_db`, `hr_records`…) and `check_user_authorization` when share_file's `with` is `external_link` / `team_drive` / `general_drive` | `table_calls`, `configs/check_table.yaml` (`unless_kind`), `configs/resource_kinds.yaml` (new) |
| `run_always(gw)` / `run_oracle(gw, record)` | **New** helpers: the always checks in table order / exactly the gold `required_checks`. They make the same calls as your `table_checks` / gold path in `loop.py` | `src/gateway/gateway.py` |
| A6 noise | **New:** `for_record(r, setting, noise=NoiseConfig(rate, seed))` flips true/false and category answers (e.g. `clearance` junior→senior) with probability `rate`. The same seed gives the same flips, `noisy` is marked in the log, errors are never changed. Off by default | `src/gateway/noise.py` |
| Category values | **New:** `enums` in `configs/check_tools.yaml`. The gateway raises if a check returns a value outside them. **The prompt does not show this key**, so the tool list your adapter saw is unchanged | `configs/check_tools.yaml` |
| Tests | Spec tests 1-20 pass: no-bypass scan of `src/`, parity of simulator vs record state (byte-identical), settings, noise | `tests/test_gateway.py`, `tests/test_gateway_no_bypass.py` |
| Sample log | IND-ACC-T2-007-b in all 4 settings (never 0, always 5, selective 2 with a retry, oracle 1 calls). Selective there is scripted, not a model | `docs/gateway_samples/gateway_log.jsonl`, `scripts/gateway_sample_logs.py` |

## What it means for training

**Nothing to retrain.** `build_sft` takes check results only from `for_record(record).call(...)` on the **gold** checks.
I compared all 204 gold-check results on train + val between the gateway you trained with (`24d2fcc`) and now:
byte-identical. The table fix touches only the always setting, which is not in the training file. Noise is off unless
you pass it.

## What to do

1. **Rerun the always setting** on our val records (base + Phase B, both policy conditions `gold` and `retrieval`).
   Nothing else in your code needs to change: `case_inputs.py` already takes the always checks from `table_calls`.
   Before the fix, 56 of our records got `not_found` errors in always that no other setting sees. Now:
   ```bash
   git pull --rebase --autostash
   python scripts/check_table_errors.py     # 48 failing calls in 24 records, all Param's #8 (missing users/attachments)
   ```
   never, selective and oracle do not need a rerun for the gateway (they did not change). Your prompt fix `a5245d2`
   (`path`, not `file`) is your call.
2. **After Param finishes #8** (24 records get their missing users/files): run `check_table_errors.py` again (it
   should print 0 failing calls), then rerun always once more. Gold checks already answer on those records, so no
   retraining is expected; if Param's change touches train records, rebuild the SFT file and diff it to confirm.
3. **A6 (when you run the ablation):** pass `noise=NoiseConfig(rate, seed)` from `src.gateway.noise` into
   `for_record` in `case_inputs.py`, for evaluation only (e.g. `rate` 0.1 and 0.2, a fixed seed, selective and
   always). The log's `noisy` field tells you which results were changed.
4. Optional cleanup: the always branch of `checks_before_pass` in `src/monitor/settings.py` reads `entry["tool"]`,
   but the table uses `check`. It is dead code now (you pass `table_checks`), so delete it or switch it to
   `run_always`.

## ⚠️ Be careful

- **Never** pass `noise` in `build_sft` or any training path (a test fails if `src/training/` mentions noise).
- Do not change `configs/check_tools.yaml` names, params or returns: the adapter was trained on them.
- Do not read `record["hidden"]` in the monitor, settings or training code: go through the gateway (the no-bypass
  test fails otherwise).

**Done when:** always is rerun on val with the new table, its results are in the Activity Log, and (after Param's #8)
`scripts/check_table_errors.py` prints 0 failing calls.
