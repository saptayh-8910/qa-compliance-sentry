.PHONY: install test test-unit test-api test-db test-e2e validate report

install:
	python3 -m venv .venv
	.venv/bin/pip install -U pip
	.venv/bin/pip install -e .
	.venv/bin/playwright install chromium

test-unit:
	.venv/bin/pytest tests/unit -v

test-api:
	.venv/bin/pytest tests/api -v -m api

test-db:
	.venv/bin/pytest tests/db -v -m db

test-e2e:
	.venv/bin/pytest tests/e2e -v -m smoke

test:
	.venv/bin/pytest tests/unit tests/api tests/db -v
	.venv/bin/pytest tests/e2e -v -m smoke

validate:
	.venv/bin/python scripts/run_validations.py

report:
	.venv/bin/pytest tests/ -v --html=reports/report.html --self-contained-html
