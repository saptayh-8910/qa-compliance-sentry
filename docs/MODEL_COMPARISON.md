# OpenAI model comparison

This record documents the first controlled external comparison for the Stage 3
grounded QA assistant. It is evidence from one small experiment, not a general
model benchmark.

## Experiment design

The test changed only the model tier and reasoning effort:

| Case | Model | Reasoning effort |
|---|---|---|
| Flagship baseline | `gpt-5.6-sol` | `medium` |
| Efficient treatment | `gpt-5.6-luna` | `high` |

Both cases received the same source chunk, question, grounding instructions,
retrieved context, output-token limit, and citation validator. Each answer had
to:

- use citation `[1]`;
- map that citation to `quality-guide.md`;
- mention both Ruff and coverage;
- complete without weakening the normal grounded-answer contract.

The run was explicitly enabled with `RUN_OPENAI_LIVE_TESTS=1`. Ordinary CI
skips both cases, so it cannot spend API credits accidentally.

## First result

Run date: 2026-08-06 UTC.

| Case | Result | Duration | Recorded answer |
|---|---|---:|---|
| Sol/Medium | Passed | 4.087 s | `Ruff and branch-aware coverage checks run before a pull request is merged. [1]` |
| Luna/High | Passed | 2.237 s | `Ruff and branch-aware coverage checks run before a pull request is merged. [1]` |

For this single simple grounded question, both configurations produced the same
correct, cited answer. Luna/High was faster in this run, but one observation is
not enough to establish a reliable latency advantage or a lower hallucination
rate.

Local evidence is generated at:

- `reports/openai-model-comparison.html`
- `reports/openai-model-comparison.xml`

The reports are ignored by Git because repeated local runs should not create
repository noise. This summary preserves the meaningful result in versioned
project history.

## What this test does not prove

This first case is intentionally narrow. It does not yet measure:

- behavior when retrieved evidence is incomplete or contradictory;
- resistance to prompt injection inside retrieved documents;
- semantic support for every claim beyond numeric citation validity;
- token usage or cost per successful answer;
- latency distributions across repeated runs;
- whether either configuration performs better on difficult synthesis tasks.

## Next comparison

The next evaluation should add a small fixed dataset containing supported,
unsupported, conflicting-evidence, and prompt-injection cases. Run each case
multiple times per configuration and record pass rate, semantic groundedness,
input/output/reasoning tokens, latency, and estimated cost per successful answer.
