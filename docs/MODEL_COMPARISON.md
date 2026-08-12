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

## Advanced evaluation matrix

The live comparison is implemented as a fixed, versioned four-case subset:

| Case | Expected behavior | Paid call per model |
|---|---|---:|
| Supported merge checks | Answer with Ruff, coverage, and the exact source | Yes |
| Unsupported ownership question | Retrieval miss and exact abstention | No |
| Conflicting retention policies | Exact abstention without choosing 14 or 30 days | Yes |
| Retrieved prompt injection | Answer the supported fact, ignore the injected command, and cite the source | Yes |

Running both configurations therefore creates eight test results but exactly
six paid calls. The no-evidence case proves that the application skips the
generator entirely. Each result records its model, reasoning effort, case ID,
pass/fail status, answer, latency, and any input/output/reasoning token counts
returned by the API. It also records context precision, context recall, Hit@K,
reciprocal rank, citation precision, and citation recall when each metric is
applicable.

The offline Stage 4 learning dataset has since grown to ten cases. The live
comparison deliberately remains on these original four cases so dataset growth
cannot silently raise the paid run from six API calls. A larger live experiment
would require a separate, explicit decision and budget.

The deterministic rubric checks observable behavior, required and forbidden
terms, exact citation sources, and human-labelled relevant chunks. Numeric model
citations are validated and mapped to canonical repository sources before
scoring, so source-name formatting differences cannot create false failures.
This makes failures explainable and stable, but it is not a complete semantic-
entailment measurement. Pricing is also not hard-coded because it can change;
cost can be calculated from the retained token counts using the official price
at analysis time. Repeated runs are still needed before comparing pass-rate or
latency distributions.

No LLM grades these results. Questions, relevant chunks, expected citation
sources, required facts, forbidden content, and expected abstentions are all
human-authored and version-controlled. The project now demonstrates that
requirement with a separate [bounded faithfulness validation](FAITHFULNESS.md).
It does not use the compared answer models as judges; any future LLM judge must
be validated against broader human-labelled evidence first.
