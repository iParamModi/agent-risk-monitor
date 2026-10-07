.PHONY: test external

test:
	pytest -q tests

external:
	bash scripts/download_external.sh
