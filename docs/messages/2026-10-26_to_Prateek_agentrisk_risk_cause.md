Hi Prateek,

The AgentRisk risk-cause labelling is assigned to you: **all 281 items. Please don't hand it over to anyone else.** I've finished the AgentRisk risk types (142 items).

Please `git pull`, then:

1. Make your labelling file (or use the one I sent you):
   `python scripts/show_agentrisk_recheck.py --cause Prateek > local_notes/agentrisk_cause_Prateek.txt`
2. Read each conversation and type your choice after `done:` in the item's first line. Choose only from that item's `CHOOSE ONE OF` options, or write `CONFUSED`. The 4 causes are explained at the top of the file.
3. Copy your labels into the sheet:
   `python scripts/import_agentrisk_labels.py --cause Prateek local_notes/agentrisk_cause_Prateek.txt`
4. Check the sheet, then push only `data/external/agentrisk_cause_recheck.csv`:
   `python scripts/show_agentrisk_recheck.py --cause --check`

Label by hand only, no LLM (CLAUDE.md §6). The driver map is in `data/external/agentrisk_map_review.md`, Q4.

The AgentRisk items aren't in git because they have no licence. If you don't have them yet, run `bash scripts/download_external.sh` and then `python -m src.external.agentrisk` first.

Thanks!
Meet
