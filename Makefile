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

# Fast subset: exclude slow/live tests and run in parallel when xdist is available
test-fast:
	@python - <<'PY'
import shutil, sys, os
if shutil.which('pytest') is None:
    print('pytest not found'); sys.exit(1)
has_xdist = 'xdist' in __import__('pkgutil').iter_modules()
cmd = os.environ.get('PYTEST_CMD','python -m pytest') + " -q -k 'not slow and not live'"
if has_xdist:
    cmd += ' -n auto'
print('Running fast tests: ' + cmd)
res = os.system(cmd)
sys.exit(res)
PY

# Run tests in parallel using pytest-xdist (-n auto); falls back to sequential if unavailable
test-parallel:
	@python - <<'PY'
import shutil, sys, os, pkgutil
if shutil.which('pytest') is None:
    print('pytest not found'); sys.exit(1)
if pkgutil.find_loader('xdist'):
    cmd = os.environ.get('PYTEST_CMD','python -m pytest') + ' -q -n auto'
else:
    print('pytest-xdist not installed; running sequentially')
    cmd = os.environ.get('PYTEST_CMD','python -m pytest') + ' -q'
print('Running: ' + cmd)
res = os.system(cmd)
sys.exit(res)
PY

# Run full test suite including reference imports (requires ALLOW_REF_IMPORTS=1)
test-all:
	ALLOW_REF_IMPORTS=1 $(PY) -m pytest -q

# Run live-model integration tests (requires local Ollama) and reference imports
# Set RUN_LIVE_OLLAMA=1 and ALLOW_REF_IMPORTS=1 to enable live tests
test-live:
	RUN_LIVE_OLLAMA=1 ALLOW_REF_IMPORTS=1 $(PY) -m pytest -q
