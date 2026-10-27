PYTHON ?= python3

.PHONY: test external eval-dummy policies records

test:
	$(PYTHON) -m pytest -q tests

# Step 5: regenerate the policy store (policies.jsonl + policies_ood.jsonl) from the seeds.
policies:
	$(PYTHON) scripts/gen_policy_store.py

# Steps 9 + 11: merge data/generated into data/records (all checks), split by seed, lock test + OOD, tool phases.
# The test files are locked: if they would change, split stops (rerun with --relock only on purpose).
records:
	$(PYTHON) -m src.data_gen.merge
	$(PYTHON) -m src.data_gen.split
	$(PYTHON) scripts/split_by_phase.py

external:
	bash scripts/download_external.sh
	$(PYTHON) -m src.external.normalize
	$(PYTHON) -m src.external.sample
	$(PYTHON) -m src.external.map_risk
	$(PYTHON) -m src.external.agentrisk
	$(PYTHON) -m src.external.count_tokens
	$(PYTHON) -m src.external.phase_a

# Step 12 check: fake runs for the 4 settings -> full report in outputs/runs/dummy_report/main.md
eval-dummy:
	$(PYTHON) scripts/make_dummy_runs.py
	$(PYTHON) -m src.eval.tables --run never=outputs/runs/dummy_never --run always=outputs/runs/dummy_always \
		--run selective=outputs/runs/dummy_selective --run oracle=outputs/runs/dummy_oracle \
		--out outputs/runs/dummy_report --title "Dummy results (fake data)"
