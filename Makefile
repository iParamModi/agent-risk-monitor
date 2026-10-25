PYTHON ?= python3

.PHONY: test external eval-dummy

test:
	$(PYTHON) -m pytest -q tests

external:
	bash scripts/download_external.sh
	$(PYTHON) -m src.external.normalize
	$(PYTHON) -m src.external.sample
	$(PYTHON) -m src.external.map_risk
	$(PYTHON) -m src.external.agentrisk
	$(PYTHON) -m src.external.count_tokens

# Step 12 check: fake runs for the 4 settings -> full report in outputs/runs/dummy_report/main.md
eval-dummy:
	$(PYTHON) scripts/make_dummy_runs.py
	$(PYTHON) -m src.eval.tables --run never=outputs/runs/dummy_never --run always=outputs/runs/dummy_always \
		--run selective=outputs/runs/dummy_selective --run oracle=outputs/runs/dummy_oracle \
		--out outputs/runs/dummy_report --title "Dummy results (fake data)"
