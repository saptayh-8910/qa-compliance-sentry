# syntax=docker/dockerfile:1

ARG PLAYWRIGHT_VERSION=1.61.0
FROM mcr.microsoft.com/playwright/python:v${PLAYWRIGHT_VERSION}-noble

ARG PLAYWRIGHT_VERSION

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --chown=pwuser:pwuser . .

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install -e ".[dev]" && \
    python -c "from importlib.metadata import version; assert version('playwright') == '${PLAYWRIGHT_VERSION}'" && \
    mkdir -p data reports && \
    chown -R pwuser:pwuser /app

USER pwuser

CMD ["python", "-m", "pytest", "tests/unit", "tests/algorithms", "tests/db", "tests/e2e/test_qa_assistant_chat.py", "-v"]
