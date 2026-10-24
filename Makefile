PYTHON ?= python3

.PHONY: test external

test:
	$(PYTHON) -m pytest -q tests

external:
	bash scripts/download_external.sh
	$(PYTHON) -m src.external.normalize
	$(PYTHON) -m src.external.sample
	$(PYTHON) -m src.external.map_risk
	$(PYTHON) -m src.external.count_tokens
