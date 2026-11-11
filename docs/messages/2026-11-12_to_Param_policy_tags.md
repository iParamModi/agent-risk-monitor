# To Param: please confirm the policy tags (from Meet, 2026-11-12)

The final system (v2) looks only at the policies that apply to the proposed action's tool, then shows the best 8. That lifted "all correct policies shown" from 0.33 to 0.80 on val. The tags (`data/policies/policy_tags.yaml`) come from the `actions` field of `policy_logic.yaml`, which your generator writes. For the report we need a person to confirm them from the **visible policy text only**, so nobody can say retrieval was told the answer.

## What to do (about 2 h, by 13 Nov)
1. Pull, open `data/policies/policy_tags_review.csv` (324 rows: 154 in-domain + 170 OOD policy texts).
2. For each row, read `text` and `applies_to` (the tools the policy is tagged with). Ask: from the text alone, does this policy apply to these tools, and to no other tool in `lma_agent/tools.yaml`?
3. Fill `ok` with `yes` or `no`. If `no`, write the tools it should apply to in `should_be` (space-separated) and a short `note`.
4. Commit only the CSV and add a line to the Activity Log in `PROGRESS.md`.

Do not change `policy_tags.yaml` or `policy_logic.yaml` yourself: I will count the disagreements for the report and decide with you whether anything has to change. This is not risk-type labelling (CLAUDE.md §6 is about risk types), so the no-LLM rule does not block you, but please do it by hand anyway: the point is a human check.
