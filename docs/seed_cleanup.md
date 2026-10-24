# Seed cleanup: make every seed use the company's tool names

**For:** Param  **From:** Prateek, 2026-10-24  **Status:** open

## Why

The team decided that the demo company (`lma_agent/`) follows the **seeds**, not the other way round
(`docs/alignment_issues.md`). Prateek is changing `lma_agent` to use the names the in-domain seeds
already use. Where seeds disagree with each other, the company takes the **majority** form, so the few
seeds using the minority form must change. After this, a seed's action can run in the company as is.

Check your progress any time:

```bash
python scripts/check_seed_vocab.py      # lists every mismatch, ends with "N seeds with problems"
```

Done = `0 seeds with problems`, plus `python scripts/validate_seeds.py` still passes.

## The shared list (contract)

Write actions (`?` = optional):

| Action | Args |
|---|---|
| `delete_file` | `file` |
| `edit_file` | `file` |
| `move_file` | `file`, `to` (folder path) |
| `share_file` | `file`, `with` (user id, contact id, `external_link`, `team_drive`, ...) |
| `write_cells` | `file`, `cells` (range like `C1:C20`), `content` |
| `send_email` | `to`, `subject`, `attachment?` |
| `grant_permission` | `user`, `resource`, `level` |
| `revoke_permission` | `user`, `resource`, `level?` |
| `transfer_money` | `from_account`, `to_account`, `amount_inr` |
| `delete_repository` | `repo` |
| `archive_repository` | `repo` |
| `create_event` | `title`, `attendees` (list) |
| `archive_record` (OOD) | `customer_id` |
| `export_customer_data` (OOD) | `customer_id`, `destination` |

Read tools (in `t2_subtypes.*.earlier_read`): `get_file_info(file)`, `get_account(account)`,
`get_repo(repo)`, `get_customer_record(customer_id)`.

**Not part of the contract (no change needed):**
- File ids: bare names (`budget.xlsx`) and full paths (`/Legal/hold/case_9.pdf`) are both fine. The company finds a file by either.
- Fact values (`internal` / `external:org_N` / `public`, `restricted`, the ~80 hidden facts): the company is adopting the seed values.

## What to change (174 seeds, but 3 of the 4 fixes are mechanical)

The seeds are written by `scripts/gen_seeds.py`, so fix the generator, not only the YAML, or the next
run brings the old names back. Keep `author`/`reviewer` as they are (renames do not change any rule).

### Fix 1: `requested_by` out of the tool args (all 150 in-domain seeds)

`requested_by` says who asked for the action. That is story context for the writer, not something the
agent passes to a tool, so it must not sit inside `proposed_action.args` / `later_write.args`.

**Recommended:** move it to a top-level field of the seed (`requested_by: user_90`) and add that field to
`configs/schemas/seed.schema.json`. The writer LLM still uses it for the conversation. If you prefer a
different place, fine; it just must not be in `args`.

### Fix 2: `share_file` recipient in-domain (8 seeds)

| Seeds | Now | Change to |
|---|---|---|
| IND-FILE-T1-006, IND-FILE-T1-014, IND-FILE-T5-002, IND-PRIV-T1-002, IND-PRIV-T1-007, IND-PRIV-T1-011 | `to:` | `with:` (same value) |
| IND-PRIV-T4-001, IND-PRIV-T4-002 | `to_folder: /Public` | **your call:** putting a file in a folder is `move_file(file, to: /Public)`; sharing it is `share_file(file, with: ...)`. Pick the one that matches the rule (P_PRIV_04) and check the gold decision is unchanged |

### Fix 3: OOD reworded seeds back to the shared names (24 seeds)

These were written with the old `lma_agent` names on purpose (the "real tools" for T2 staling). Now that
the company switches to the seed names, they must switch too. Only names change; values, rules, wording
and gold stay the same.

| Old (`lma_agent` style) | New |
|---|---|
| `grant_access(user_id, resource, role)` | `grant_permission(user, resource, level)` |
| `share_file(path, recipient, permission)` | `share_file(file, with)`: `path` -> `file`, `recipient` -> `with`, drop `permission` |
| `delete_file(path)` | `delete_file(file)` |
| `write_cells(path, range, values)` | `write_cells(file, cells, content)` |
| `send_email(to, subject, body, attachments)` | `send_email(to, subject, attachment)`: one attachment, `body` goes (story text) |
| `transfer_money(amount, ...)` | `transfer_money(amount_inr, ...)` |
| `get_file_info(path)` | `get_file_info(file)` |
| `get_account(account_id)` | `get_account(account)` |

Seeds: OOD-ACC-T1-001/002, T2-001/002, T3-001, T4-001; OOD-CAL-T1-001, T2-001; OOD-FILE-T1-001/002,
T2-001/002; OOD-FIN-T1-001/002, T2-001/002, T3-001, T4-001; OOD-PRIV-T1-001/002, T2-001/002/003, T5-001.

`level` values: in-domain seeds use `read` / `write` / `admin`, so map `viewer` -> `read`, `editor` -> `write`,
`admin` -> `admin`.

### Questions for you (answer in this file or tell Prateek)

1. `to_folder` seeds: `move_file` or `share_file`?
2. `requested_by`: OK as a top-level field?
3. Anything in this list you think is **intended** (e.g. a deliberate OOD rename)? Then we mark it and
   the checker will skip it, instead of changing it.

## When done

Run both checks, update `PROGRESS.md` (Completed + Activity Log), commit and push the generator,
the seeds and the schema together.
