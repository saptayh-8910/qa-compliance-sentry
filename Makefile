.PHONY: install test test-local test-unit test-algorithms test-api test-db \
	test-e2e test-chatbot-e2e test-ai-external validate validate-pipeline \
	retrieve-docs answer-docs chat-docs evaluate-rag answer-docs-openai report \
	analyze-sample \
	lint format format-check coverage quality docker-build docker-test \
	docker-quality docker-external

DOCKER_IMAGE ?= qa-compliance-sentry:0.8.0
DOCKER_RUN = docker run --rm --init --ipc=host
DOCKER_REPORTS = -v "$(CURDIR)/reports:/app/reports"
DOCKER_ENV_ARGS ?=

install:
	python3 -m venv .venv
	.venv/bin/pip install -U pip
	.venv/bin/pip install -e ".[dev]"
	.venv/bin/playwright install chromium

test-unit:
	.venv/bin/pytest tests/unit -v

test-algorithms:
	.venv/bin/pytest tests/algorithms -v

test-api:
	.venv/bin/pytest tests/api -v -m api

test-db:
	.venv/bin/pytest tests/db -v -m db

test-e2e:
	.venv/bin/pytest tests/e2e -v -m smoke

test-chatbot-e2e:
	mkdir -p reports
	.venv/bin/pytest tests/e2e/test_qa_assistant_chat.py -m chatbot -v \
		-o junit_family=legacy \
		--html=reports/chatbot-e2e.html --self-contained-html \
		--junitxml=reports/chatbot-e2e.xml

test-ai-external:
	mkdir -p reports
	# Four cases x two models; no-evidence cases skip generation = six paid calls.
	RUN_OPENAI_LIVE_TESTS=1 .venv/bin/pytest \
		tests/api/test_openai_responses.py -m "external and ai" -v \
		--durations=0 \
		-o junit_family=legacy \
		--html=reports/openai-model-comparison.html --self-contained-html \
		--junitxml=reports/openai-model-comparison.xml

test:
	.venv/bin/pytest tests/unit tests/algorithms tests/api tests/db -v
	.venv/bin/pytest tests/e2e -v -m smoke

test-local:
	.venv/bin/pytest tests/unit tests/algorithms tests/db -v

lint:
	.venv/bin/ruff check .

format:
	.venv/bin/ruff check --fix .
	.venv/bin/ruff format .

format-check:
	.venv/bin/ruff format --check .

coverage:
	.venv/bin/pytest tests/unit tests/algorithms tests/db -v \
		--cov=api --cov=bug_tracker --cov=db --cov=log_analyzer \
		--cov=learning_algorithms \
		--cov=pipeline_validator \
		--cov=qa_assistant \
		--cov-report=term-missing \
		--cov-report=xml:reports/coverage.xml \
		--cov-report=html:reports/coverage \
		--html=reports/local-report.html --self-contained-html \
		--junitxml=reports/local-junit.xml

quality: lint format-check coverage test-chatbot-e2e

docker-build:
	docker build --pull -t $(DOCKER_IMAGE) .

docker-test: docker-build
	$(DOCKER_RUN) $(DOCKER_IMAGE)

docker-quality: docker-build
	mkdir -p reports
	$(DOCKER_RUN) $(DOCKER_REPORTS) $(DOCKER_IMAGE) /bin/bash -lc \
		'ruff check . && ruff format --check . && \
		python -m pytest tests/unit tests/algorithms tests/db -v \
		--cov=api --cov=bug_tracker --cov=db --cov=log_analyzer \
		--cov=learning_algorithms \
		--cov=pipeline_validator \
		--cov=qa_assistant \
		--cov-report=term-missing \
		--cov-report=xml:reports/coverage.xml \
		--cov-report=html:reports/coverage \
		--html=reports/docker-local-report.html --self-contained-html \
		--junitxml=reports/docker-local-junit.xml'

docker-external: docker-build
	mkdir -p reports
	$(DOCKER_RUN) $(DOCKER_REPORTS) $(DOCKER_ENV_ARGS) $(DOCKER_IMAGE) \
		python -m pytest tests/api tests/e2e -m external -v \
		--html=reports/docker-external-report.html --self-contained-html \
		--junitxml=reports/docker-external-junit.xml

analyze-sample:
	.venv/bin/log-analyzer analyze examples/sample_logs.jsonl \
		--top 3 --output reports/sample-log-analysis.json

validate-pipeline:
	.venv/bin/pipeline-validator validate examples/pipeline_dependencies.json

retrieve-docs:
	.venv/bin/qa-assistant retrieve \
		"Why separate scheduled external checks from merge-blocking tests?" \
		--source docs --top 3

answer-docs:
	.venv/bin/qa-assistant answer \
		"Why separate scheduled external checks from merge-blocking tests?" \
		--source docs --top 3

chat-docs:
	.venv/bin/qa-assistant chat --source docs --top 3

evaluate-rag:
	mkdir -p reports
	.venv/bin/qa-assistant evaluate --output reports/rag-evaluation.json

# Explicitly makes a paid OpenAI API request.
answer-docs-openai:
	.venv/bin/qa-assistant answer \
		"Why separate scheduled external checks from merge-blocking tests?" \
		--source docs --top 3 --provider openai

validate:
	.venv/bin/python scripts/run_validations.py

report:
	.venv/bin/pytest tests/ -v --html=reports/report.html --self-contained-html
