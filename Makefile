.PHONY: install test test-local test-unit test-api test-db test-e2e validate report \
	lint format format-check coverage quality

install:
	python3 -m venv .venv
	.venv/bin/pip install -U pip
	.venv/bin/pip install -e ".[dev]"
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

test-local:
	.venv/bin/pytest tests/unit tests/db -v

lint:
	.venv/bin/ruff check .

format:
	.venv/bin/ruff check --fix .
	.venv/bin/ruff format .

format-check:
	.venv/bin/ruff format --check .

coverage:
	.venv/bin/pytest tests/unit tests/db -v \
		--cov=api --cov=bug_tracker --cov=db \
		--cov-report=term-missing \
		--cov-report=xml:reports/coverage.xml \
		--cov-report=html:reports/coverage \
		--html=reports/local-report.html --self-contained-html \
		--junitxml=reports/local-junit.xml

quality: lint format-check coverage

validate:
	.venv/bin/python scripts/run_validations.py

report:
	.venv/bin/pytest tests/ -v --html=reports/report.html --self-contained-html
