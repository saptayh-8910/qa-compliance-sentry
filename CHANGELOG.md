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
- Interactive `qa-assistant chat` sessions that reuse one document index across
  supported, unsupported, and subsequent questions.
- Deterministic subprocess chatbot E2E coverage for a supported answer, verified
  source, abstention, and clean exit without an API key or network request.
- Dedicated chatbot HTML and JUnit evidence retained by merge-blocking CI.
- Stage 4 versioned JSON evaluation contract with run metadata, aggregate and
  case-level metrics, explainable checks, failures, duration, and optional token
  usage.
- Atomic `qa-assistant evaluate` report export plus a zero-cost
  `make evaluate-rag` workflow and retained CI artifact.
- Stage 4 evaluation-reporting design documenting non-applicable metric values,
  gating behavior, dashboard consumption, and semantic-judge validation.
- Responsive standalone RAG evaluation dashboard with aggregate quality cards,
  per-case diagnostics, Passed/Failed filters, citations, checks, and telemetry.
- Strict v1 dashboard input validation and HTML escaping for adversarial answer,
  citation, check, error, case, and run metadata fields.
- Installed `qa-assistant dashboard` command plus the zero-cost
  `make dashboard-rag` workflow and retained CI HTML artifact.
- Always-visible plain-English metric definitions, result interpretations, and
  case evaluation criteria for readers without RAG or QA terminology.
- Stage 4 implementations of Edit Distance, Kth Largest Element in a Stream,
  and Maximum Average Subarray with canonical, edge-case, and QA-oriented tests.
- Literal answer-regression comparison with edit count and normalized surface
  similarity, explicitly separated from semantic correctness or groundedness.
- Bounded evaluation-score trend analysis with a kth-highest threshold and best
  fixed-size rolling average.
- Ten-case human-labelled RAG dataset covering supported answers, multi-source
  synthesis, distracting retrieval, lexical paraphrase failure, stale policy,
  conflicting evidence, and supported or unsupported prompt injection.
- Case-specific expected context precision and recall so intentional retrieval
  misses and distractors remain diagnostic without producing false rubric
  failures.
- Evaluation report schema v2 with the original question and expected
  answer-or-abstain behavior on every case, plus legacy v1 dashboard support.
- Plain-English expected outcomes on dashboard case cards so non-technical
  readers can interpret what each result was supposed to do.
- Repeated RAG benchmark with three zero-cost repetitions across ten cases,
  nearest-rank p50/p95 latency, sample pass rate, verdict stability, exact
  answer-and-citation consistency, and optional token summaries.
- Versioned benchmark JSON schema plus a safe standalone dashboard that explains
  every criterion and distinguishes a consistent failure from a correct result.
- Explicit paid-benchmark confirmation that blocks OpenAI execution and reports
  the projected call count unless `--confirm-paid` is supplied.

### Changed

- Bumped the package and default Docker image version to `0.6.0` for the Stage 3
  algorithm milestone.
- Bumped the package and default Docker image version to `0.7.0` for Stage 3
  completion.
- Marked Stage 3 complete and made the Stage 4 evaluation dashboard the next
  roadmap milestone.
- Expanded deterministic quality validation to 200 tests at 96.26%
  branch-aware coverage.
- Expanded deterministic quality validation to 204 tests at 96.34%
  branch-aware coverage, plus one dedicated subprocess chatbot E2E journey.
- Bumped the package and default Docker image version to `0.8.0` for the Stage 4
  evaluation-reporting foundation.
- Marked Stage 4 in progress with visualization, dataset growth, repeated
  latency sampling, and validated semantic faithfulness still ahead.
- Expanded deterministic quality validation to 223 tests at 96.60% branch-aware
  coverage, plus the retained chatbot E2E journey.
- Bumped the package and default Docker image version to `0.9.0` for the Stage 4
  metric dashboard milestone.
- Marked the Stage 4 metric dashboard complete while keeping dataset growth,
  repeated latency sampling, algorithm lessons, and validated semantic
  faithfulness ahead.
- Expanded deterministic quality validation to 238 tests at 95.24% branch-aware
  coverage, plus the retained chatbot E2E journey.
- Bumped the package and default Docker image version to `0.10.0` for the Stage
  4 algorithm foundations milestone.
- Completed the twelve-problem, three-per-stage interview learning roadmap.
- Expanded deterministic quality validation to 278 tests at 95.50% branch-aware
  coverage, plus the retained chatbot E2E journey.
- Bumped the package and default Docker image version to `0.11.0` for the
  expanded Stage 4 evaluation dataset milestone.
- Completed the larger labelled-dataset roadmap item while keeping the paid
  Sol/Luna comparison on its original four-case, six-call budget.
- Expanded deterministic quality validation to 284 tests at 95.56%
  branch-aware coverage, plus the retained chatbot E2E journey.
- Bumped the package and default Docker image version to `0.12.0` for the Stage
  4 latency and stability benchmarking milestone.
- Completed the repeated latency and reproducibility roadmap item; validated
  semantic faithfulness remains the final planned Stage 4 capability.
- Expanded deterministic quality validation to 311 tests at 92.70%
  branch-aware coverage, plus the retained chatbot E2E journey.

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
