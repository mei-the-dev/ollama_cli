# Makefile — common developer tasks

.PHONY: test-local test

# Run the focused local checks: fast tests, interactive CLI test, placeholder scanner
PY := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python)

test-local:
	$(PY) scripts/local_test_runner.py

# CLI report: run focused CLI tests and render report
cli-report:
	$(PY) scripts/cli_report.py

# Run factory-generated tests and validate results
factory-run:
	$(PY) scripts/test_orchestrator.py

factory-generate:
	$(PY) scripts/test_factory.py generate

# Full test suite
test:
	$(PY) -m pytest -q

# Run full test suite including reference imports (requires ALLOW_REF_IMPORTS=1)
test-all:
	ALLOW_REF_IMPORTS=1 $(PY) -m pytest -q

# Run live-model integration tests (requires local Ollama) and reference imports
# Set RUN_LIVE_OLLAMA=1 and ALLOW_REF_IMPORTS=1 to enable live tests
test-live:
	RUN_LIVE_OLLAMA=1 ALLOW_REF_IMPORTS=1 $(PY) -m pytest -q
