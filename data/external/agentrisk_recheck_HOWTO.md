# AgentRisk risk-type labelling: how to

**Who:** Prateek 71 (his 35 + Meet's 36, handed over 2026-10-26) · Param 36 · Moiesha 35 (142 items, random split, the same mix per share)
**Time:** about 30–40 minutes per 35 items
**Rule:** label by hand. **No Claude, ChatGPT or any LLM** (CLAUDE.md §6). LLM-made labels are rejected and redone.

## What this is

AgentRisk (our SemEval shared task) labels each item with 1–2 **harm domains** ("what may be harmed").
We turn them into our 6 risk types with the map in `agentrisk_map_review.md`. Most items are decided by
the map. These 142 UNSAFE items need a person:

| `reason` | Items | Why a person is needed |
|---|---|---|
| `two domains` | 98 | two harm domains that map to **two different types**, e.g. Privacy + Security |
| `mixed domain` | 44 | Operational / Service or Information Quality, which cover several of our types |

You **only choose from the row's `options`** (2 types for `two domains`, 3–4 for `mixed domain`), or
`CONFUSED`. That keeps every label one of the item's own harms, so the classes are not pushed out of balance.

## 1. Get the items on your computer (they are not in git: no licence)

```bash
git pull
pip install jsonschema pyyaml          # if not installed yet
bash scripts/download_external.sh      # downloads AgentRisk (pinned version) into data/raw/agentrisk/
python -m src.external.agentrisk       # converts it into data/external/agentrisk/AR-*.json
```

## 2. See your items

```bash
python scripts/show_agentrisk_recheck.py <YourName>            # all your items, e.g. Param
python scripts/show_agentrisk_recheck.py <YourName> AR-280     # one item
```

Each item shows the conversation, then:

```
>>> PROPOSED ACTION (not yet run): ...
>>> CHOOSE ONE OF: SECURITY | PRIVACY_LEAKAGE   (or CONFUSED)
AgentRisk labels: severity 4 | harm domains: Privacy / Confidentiality (your map: PRIVACY_LEAKAGE),
                  Security / System Integrity (your map: SECURITY) | risk drivers: ...
```

The "AgentRisk labels" line holds the dataset's own labels and our map, not anyone's suggestion.

## 3. Decide

Use `data/external/risk_type_categories.txt` (the guide), and:

- **`two domains`:** label the harm that the **proposed action itself** causes (guide Rule 2:
  the direct effect, not a later consequence). Physical / Health, Legal, Reputational, Environmental and
  Discrimination count as OTHER.
- **`mixed domain`:** situation rule (Meet, 2026-10-26):

  | Situation | Type |
  |---|---|
  | system made unstable, forced shutdown, processes killed | SECURITY |
  | files moved or hidden without consent | SECURITY |
  | deleting apps or files, clearing data, overwriting records | DATA_LOSS |
  | physical or emergency harm (dispatch, health) | OTHER |
  | the item's other domain fits better (e.g. money moves) | that option, e.g. FINANCIAL_LOSS |

- Still unsure: write `CONFUSED` and say in `recheck_note` which options you are torn between.
  The team settles all CONFUSED rows together.

## 4. Write it down

In `data/external/agentrisk_recheck.csv`, on **your rows only**:

- `recheck_type`: one option from the row, spelled exactly (e.g. `PRIVACY_LEAKAGE`), or `CONFUSED`
- `recheck_note`: a few words when the case was hard (optional)

Save as **CSV UTF-8**. Do not sort, reorder or delete rows or columns.

## 5. Check and push

```bash
python scripts/show_agentrisk_recheck.py --check    # shows filled counts; lists any value that is not an option
git add data/external/agentrisk_recheck.csv
git commit -m "add <YourName>'s AgentRisk risk-type labels"
git pull --rebase --autostash && git push
```

Then tick your row in `PROGRESS.md` (Next Up). When all four are done, Meet applies the labels
(`src/external/agentrisk.py` map step).
