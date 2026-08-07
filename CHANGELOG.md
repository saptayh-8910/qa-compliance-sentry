# Changelog

All notable project changes are recorded here. Dates use UTC and each released
milestone links to the pull request that introduced it.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses semantic versioning for milestone tags.

## [Unreleased]

### Added

- Permanent changelog and project-history documentation.
- Stage 3 document ingestion for local Markdown and text sources.
- Heading-aware chunking that ignores heading-like lines inside fenced code.
- Deterministic BM25-style lexical retrieval with stable tie-breaking.
- Bounded, numbered source-and-heading citation context.
- Installed `qa-assistant retrieve` command and runnable `make retrieve-docs`
  example.
- Twenty-six focused ingestion, retrieval, service, and CLI tests.
- Provider-neutral answer-generator request contract with grounding instructions.
- Offline extractive answer baseline for end-to-end local demonstrations.
- Fail-closed citation validation and source mapping for generated answers.
- Evidence-first abstention that skips generation when retrieval has no match.
- Installed `qa-assistant answer` command and runnable `make answer-docs` example.
- Fifteen focused generation, validation, orchestration, and answer-CLI tests.
- OpenAI Responses API answer adapter with separated instructions and retrieved
  evidence, disabled response storage, bounded output, and configurable model.
- Explicit `--provider openai` CLI path while keeping offline extraction as the
  zero-cost default.
- Mocked adapter and CLI contract tests plus an opt-in paid external smoke test.
- Local `.env` credential loading with a tracked, secret-free example.
- Explicit GPT-5.6 reasoning-effort configuration and a controlled, two-call
  Sol/Medium versus Luna/High external comparison with retained test evidence.
- First controlled model-comparison result: both configurations returned the
  same correct citation-grounded answer; Luna/High was faster in this single
  run, without treating one observation as a general performance conclusion.
- Exact generator abstention contract for incomplete or unresolved conflicting
  evidence, without weakening citation requirements for factual answers.
- Four-case grounding evaluation dataset covering supported answers, retrieval
  misses, conflicting evidence, and prompt injection in untrusted documents.
- Explainable checks for expected behavior, required and forbidden terms, and
  exact citation sources, exercised with deterministic fake generators.
- Human-labelled relevant chunks with context precision/recall, Hit@K, mean
  reciprocal rank, citation precision/recall, and aggregate pass-rate metrics.
- Deterministic grading documentation that separates retrieval, generation,
  citation, and safety failures without relying on an unvalidated LLM judge.
- Opt-in Sol/Medium versus Luna/High adversarial matrix designed for exactly six
  paid calls, with latency and API token usage retained in HTML/JUnit evidence.
- Dedicated README AI Quality Engineering matrix covering hallucination
  controls, prompt injection, retrieval and citation metrics, latency evidence,
  cross-model regression, and the remaining Stage 4 limitations.
- Stage 3 implementations of Valid Parentheses, LRU Cache, and Trie with
  canonical interview cases and QA/RAG-oriented tests.
- Fail-closed generated-answer delimiter validation before citation parsing.
- Fixed-capacity O(1) LRU caching for ranked searches and deterministic trie
  prefix lookup for indexed source paths.

### Changed

- Bumped the package and default Docker image version to `0.6.0` for the Stage 3
  algorithm milestone.
- Expanded deterministic quality validation to 200 tests at 96.26%
  branch-aware coverage.

## [0.4.1] - 2026-08-05

### Added

- Stage 1 learning implementations for Two Sum, Contains Duplicate, and Binary
  Search.
- Sixteen canonical and QA-oriented foundation test cases.
- Complexity notes, interview prompts, and guidance about when production code
  should prefer database constraints, built-ins, or indexed queries.

### Changed

- Expanded deterministic quality coverage to 84 tests and 95.73% branch-aware
  coverage.
- Included `learning_algorithms` in packaging, CI, and Docker quality gates.

Merged in [PR #5](https://github.com/saptayh-8910/qa-compliance-sentry/pull/5)
at commit `0cbf054`.

## [0.4.0] - 2026-08-05

### Added

- JSONL log analyzer for recurring-failure ranking and incident grouping.
- Named CI pipeline validator for circular dependency detection.
- Stage 2 implementations of Top K Frequent Elements, Merge Intervals, and
  Course Schedule.
- Installed `log-analyzer` and `pipeline-validator` commands with runnable
  examples.
- Twelve-problem, three-per-stage algorithm learning roadmap.

### Changed

- Expanded deterministic quality coverage to 68 tests and 95.41% branch-aware
  coverage.

Merged in [PR #4](https://github.com/saptayh-8910/qa-compliance-sentry/pull/4)
at commit `cfc9e8c`.

## [0.3.0] - 2026-08-04

### Added

- Pinned Playwright 1.61.0 Docker environment.
- Non-root container execution using `pwuser`.
- Docker targets for deterministic, quality, and external test runs.
- Container smoke test in GitHub Actions.
- Host-mounted HTML, XML, JUnit, coverage, and browser-test evidence.

### Verified

- Twenty deterministic tests and five external API/Chromium tests passed in
  Docker at 95.88% coverage.

Merged in [PR #3](https://github.com/saptayh-8910/qa-compliance-sentry/pull/3)
at commit `8e7222e`.

## [0.2.0] - 2026-08-03

### Added

- GitHub Actions quality gates for pull requests and `main`.
- Python 3.11–3.14 compatibility matrix.
- Ruff lint and formatting checks plus an 85% branch-aware coverage gate.
- Scheduled and manually triggered external API/Playwright workflow.
- Uploaded HTML, XML, JUnit, and failure artifacts.

### Changed

- Increased the full suite to 25 tests and the deterministic suite to 20 tests
  at 95.88% coverage.

Merged in [PR #2](https://github.com/saptayh-8910/qa-compliance-sentry/pull/2)
at commit `a5e8512`.

## [0.1.0] - 2026-07-31

### Added

- Environment-based test configuration.
- Read-only SQLite validation separated from database seeding.
- Negative database, CLI, and isolated API-client tests.
- Deterministic offline test target and explicit external-test marker.
- Atomic JSON persistence for the bug tracker.
- Project motivation and test-strategy documentation.

### Changed

- Hardened Stage 1 so validation detects bad data instead of only proving that
  known-good seed data passes.

### Verified

- Nineteen full-suite tests, fourteen deterministic tests, and seven database
  validation checks passed.

Merged in [PR #1](https://github.com/saptayh-8910/qa-compliance-sentry/pull/1)
at commit `ed550d7`.

[Unreleased]: https://github.com/saptayh-8910/qa-compliance-sentry/compare/v0.4.1...HEAD
[0.4.1]: https://github.com/saptayh-8910/qa-compliance-sentry/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/saptayh-8910/qa-compliance-sentry/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/saptayh-8910/qa-compliance-sentry/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/saptayh-8910/qa-compliance-sentry/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/saptayh-8910/qa-compliance-sentry/releases/tag/v0.1.0
