# To Prateek: 🔴 HIGH PRIORITY: always-setting checks that fail (check table)

**Why:** the always setting runs the fixed checks of `configs/check_table.yaml`. On 56 of our records (28 seeds) some
of these come back `not_found`, although the oracle (gold) checks all answer. So always sees an error the other
settings never see, and the "selective vs always" comparison is unfair. Seen in the Kaggle eval on val
(`outputs/kaggle/our_eval/`) and on all 528 records with:

```bash
python scripts/check_table_errors.py      # lists every failing call; exit 1 while any is left
```

Param has the state gaps (other rows of that output), you have the table rows.

## What to do

1. **grant_permission → `check_file_sharing(path=resource)` on a system** (44 records, 22 seeds: IND-ACC-T1-001/003/004/006/008/009/010/011/012/013/014, IND-ACC-T4-001/002/003, IND-ACC-T5-001…005, OOD-ACC-T1-001/002, OOD-ACC-T4-001).
   The resource is a system, dataset or repo (`prod_db`, `hr_records`, `ci_system`, `/repos/payments-core`…), not a
   file or folder, so the file check has nothing to answer. The row cannot just go: 27 grant_permission golds use
   `check_file_sharing` on real folders. Suggestion: `table_calls` also gets the state and skips the file check
   when the resource is not a file or folder there (a real system knows what kind of resource it is).
2. **share_file → `check_user_authorization(user=with)` when `with` is a link or drive** (12 records, 6 seeds:
   IND-FILE-T1-006/010/014, IND-PRIV-T1-002/007/011; targets `external_link`, `team_drive`, `general_drive`).
   They are not users. Skip the user check for these targets (a fixed list in `check_table.yaml`), or let the
   simulator answer them.
3. Not a bug: 2 `invalid_args` in the eval are the base model writing `file` instead of `path` for
   `check_file_sharing`. The gateway answered correctly. Do not rename tool arguments.

## ⚠️ Be careful

- Change only the always table (`configs/check_table.yaml`, `table_calls`). Do not change the gold required checks, the
  tool list or tool descriptions shown in the prompt: the Phase B adapter was trained on them.
- A skip rule must not hide Param's gaps: skip by the kind of resource or target, never "skip when not found".
- No record changes, so no relock. Add a Changelog row in `docs/decisions.md`.

**Done when:** `scripts/check_table_errors.py` shows no grant_permission or link/drive rows, the tests pass, and you tell
Meet, who reruns the always setting.
