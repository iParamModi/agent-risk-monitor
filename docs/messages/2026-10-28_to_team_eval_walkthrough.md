# To everyone (Prateek, Param, Moiesha): 📄 please read the eval walkthrough PDF

**File:** `docs/reports/our_eval_walkthrough.pdf` (31 pages; pull first). It shows how our monitor actually runs on our
records, from the Kaggle run on the 40 val records (base Qwen3-8B and the Phase B adapter).

## What is in it

1. **How one case runs (diagram):** what goes where. The visible part goes to the retriever, then the prompt, then the
   model. The model asks for checks and the gateway answers them from the hidden state. Gold is used only for scoring.
2. **The 4 settings (diagram):** never / always / oracle / selective, with the retry after a tool error.
3. **One of our records** as stored, and who reads which part.
4. **The exact prompt** the model gets, before and after a check.
5. **Results:** Phase B beats the base model in every setting. Selective with gold policies gets 34/40 and oracle
   39/40.
6. **18 real examples**: every model answer and every gateway call with its result, including retries after
   `not_found` / `invalid_args`.

## What to look at for your part

- **Param:** examples 13, 14 and 17 show what a user or file missing from a record's state does to a run (HIGH
  PRIORITY #8). The record format is in section 2.
- **Prateek:** the always-setting rows in each example show the check-table calls. Your #7 fix is verified:
  `scripts/check_table_errors.py` is down from 104 to 48 failing calls, all in Param's 24 records.
- **Moiesha:** sections 1–4 explain the whole loop. The examples show how T2 variants (a–d) behave.

Regenerate it after any new run: `python scripts/make_eval_pdf.py`. The same examples are also in Markdown:
`docs/reports/our_eval_examples.md`.
