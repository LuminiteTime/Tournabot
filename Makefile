PYTHON := .venv/bin/python
PIP := .venv/bin/pip
PYTEST := $(PYTHON) -m pytest

.PHONY: install install-test test-smoke

install:
	$(PIP) install -r requirements.txt

install-test:
	$(PIP) install -r requirements.txt -r requirements-test.txt

test-smoke:
	$(PYTEST) -q tests/integration/test_container_smoke.py
