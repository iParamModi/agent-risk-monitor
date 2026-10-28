# To Param: 🔴 HIGH PRIORITY: users and files missing from record states

**Why:** the proposed action names a user, contact or file that the record's hidden state does not have. When the
always setting checks it, the gateway answers `not_found` ("no user named user_60"); a real company system would
know them. 24 records (8 seeds). Seen in the Kaggle eval on val and on all 528 records with:

```bash
python scripts/check_table_errors.py      # lists every failing call; exit 1 while any is left
```

Prateek has the check-table rows (grant_permission on systems, link/drive targets), you have these.

## What to do (seed state → `make records`)

1. **Share / email target missing** (18 records):
   | Seed | Missing | Records |
   |---|---|---|
   | IND-FILE-T2-003 | user `user_60` | a–d (val) |
   | IND-FILE-T2-007 | user `user_61` | a–d (test) |
   | IND-PRIV-T2-003 | user `user_80` | a–d (train) |
   | IND-PRIV-T2-006 | user `user_81` | a–d (train) |
   | IND-FILE-T5-002 | `partner` (recipient and user check) | v1, v2 (test) |
2. **Email attachment missing from `files`** (6 records):
   | Seed | Missing file | Records |
   |---|---|---|
   | IND-CAL-T1-004 | `invite.ics` | A, B (val) |
   | IND-PRIV-T5-002 | `pii_1.csv` | v1, v2 (test) |
   | OOD-CAL-T1-001 | `/calendar/invites/kickoff_2026_03.ics` | A, B (OOD) |

Give each one values that follow the seed story (team, role, is_external / classification, folder).

## ⚠️ Be careful

- Do not change any gold or `key_facts`. The added entity must not decide the case: the same entity with the same
  values in every record of the pair or variant set (A/B, a–d, v1/v2), or it leaks the label.
- For IND-PRIV-T5-002, the facts that disagree on purpose stay as they are. Only the file is added.
- Do not edit the visible text (for `partner`, add an entity with that id instead of renaming it).
- Edit seeds, then `make records`; no hand edits of `data/records/`. `scripts/changed_records.py` must list only
  these 24 records, with only `hidden.state` changed. Then `split --relock` (8 test and 2 OOD records change) and
  add a Changelog row in `docs/decisions.md`.

**Done when:** `scripts/check_table_errors.py` shows none of these rows, `make records` reports 0 problems, the lock test
passes, and you tell Meet.
