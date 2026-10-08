PYTHON ?= python3

.PHONY: test external

test:
	$(PYTHON) -m pytest -q tests

external:
	bash scripts/download_external.sh
	$(PYTHON) -m src.external.normalize
