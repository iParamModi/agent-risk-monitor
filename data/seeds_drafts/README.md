# Draft seeds (not yet part of the dataset)

Train-only seeds drafted on 2026-10-27 (check tools, group A rule: every in-domain check tool needs at least one
train seed). They live here, not in `data/seeds/`, until they are reviewed and have policies and records, so
`make test` keeps passing.

To add one: Param reviews it (`reviewer`), adds its new policy with the policy generator, moves it to
`data/seeds/in_domain/`, and generates its 2 records; Meet lists it as `train` in `data/records/splits.yaml`
(with a Changelog row). `scripts/check_tool_coverage.py` already counts these seeds as new train seeds.

The 2026-10-27 batch (IND-ACC-T1-013/014, IND-CAL-T1-005, IND-REPO-T1-010/011) was reviewed by Param and promoted
to `data/seeds/in_domain/` on 2026-10-28 (policies P_ACC_32/33, P_CAL_12, P_REPO_19/20 added; 10 records generated).
Meet still needs to list the 5 seeds as `train` in `data/records/splits.yaml` + Changelog.
