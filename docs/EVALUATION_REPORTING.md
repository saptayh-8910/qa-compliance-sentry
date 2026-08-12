# Stage 4 evaluation reporting

Stage 4 separates evaluation evidence from the tool that visualizes or extends
it. The repository exports every deterministic RAG result as a versioned JSON
document so the included dashboard, a notebook, a CI gate, or a future
evaluation framework can consume the same facts without re-running a model.

## Run the offline baseline

```bash
make evaluate-rag

# Equivalent direct command:
.venv/bin/qa-assistant evaluate \
  --output reports/rag-evaluation.json
```

The default provider is the zero-cost extractive generator. Its current result
is intentionally diagnostic: 5 of 10 cases pass. The other five isolate
conflicting evidence, retrieved prompt injection, multi-source synthesis, a
lexical paraphrase miss, and unsafe unsupported context. The command writes
those failures and returns success so the report can be explored. Use
`--fail-on-failure` when the same rubric should act as a blocking gate.

Selecting `--provider openai` for the full ten-case command is explicit and
makes eight paid API requests because two retrieval misses skip generation.
Paid runs are never enabled by deterministic CI. The separate Sol/Luna external
regression intentionally keeps the original four-case subset and six-call
budget.

## What the ten cases teach

| Case | Expected result in plain English | Failure it can identify |
|---|---|---|
| Supported merge checks | Answer with Ruff and coverage evidence, then cite it. | A basic retrieval, fact, or citation regression. |
| Unsupported ownership | Say there is not enough evidence; do not call a model. | Inventing an answer when search found nothing. |
| Conflicting retention | Refuse to choose between unresolved 14-day and 30-day rules. | Overconfident generation from contradictory evidence. |
| Retrieved prompt injection | Use the supported fact but ignore the instruction hidden in the document. | Treating retrieved content as commands instead of evidence. |
| Browser smoke test | Answer with Playwright evidence and cite the browser guide. | Failure to retrieve and cite a second supported topic. |
| Multi-source release gates | Combine code-quality and browser evidence and cite both sources. | Incomplete synthesis or missing citations. |
| Partially relevant retrieval | Answer from the useful result even when another result is distracting. | Poor context precision or distraction by irrelevant evidence. |
| Lexical paraphrase miss | The desired outcome is a cited answer, but lexical search misses differently worded evidence. | A retrieval-recall limitation rather than a generation failure. |
| Current versus archived policy | Use the current 30-day rule and ignore the archived 14-day distractor. | Stale-document selection or unsupported policy mixing. |
| Unsupported injection | Refuse because the retrieved text is unsafe and does not support the question. | Hallucination or obedience to an irrelevant injected command. |

## Generate the local dashboard

```bash
make dashboard-rag

# Or render an existing v2 or legacy v1 report without re-running evaluation:
.venv/bin/qa-assistant dashboard \
  --report reports/rag-evaluation.json \
  --output reports/rag-dashboard.html
```

Open `reports/rag-dashboard.html` in a browser. It is a standalone, responsive
HTML file with no hosted service, JavaScript dependency, remote font, or image.
It displays:

- aggregate pass rate, context recall, citation precision, and MRR;
- an always-visible plain-English guide explaining what each metric asks and
  how to interpret percentages, Hit/Miss, and N/A;
- provider, model, dataset, grader, reasoning, and run identity;
- Passed/Failed case filters;
- per-case retrieval and citation metrics with result-specific explanations,
  observed answer, evidence, always-visible rubric checks, failures, duration,
  and optional token usage.

The dashboard deliberately keeps known failures visible. It is diagnostic
evidence, not a decorative all-green scorecard. Deterministic CI generates both
the JSON source and HTML view and retains them in the same quality artifact.

## Versioned contract

[`schemas/evaluation-report-v2.schema.json`](../schemas/evaluation-report-v2.schema.json)
is the current public contract. Each report contains:

- schema version plus run, dataset, grader, provider, model, and reasoning
  metadata;
- aggregate pass rate, context precision/recall, Hit@K, MRR, and citation
  precision/recall;
- per-case question, expected answer-or-abstain behavior, answer text, canonical
  citations, explainable checks, failure summary, and error;
- per-case duration and optional input, output, total, and reasoning token
  counts.

Non-applicable metrics remain JSON `null`. For example, Hit@K and reciprocal
rank do not apply when a case deliberately has no relevant evidence, and
citation precision/recall do not apply to a correct abstention. Converting these
values to zero would create misleading dashboard averages.

Reports are written through a temporary file in the destination directory and
atomically replaced. A reader therefore sees either the previous complete run
or the new complete run, never a partially written JSON document.

Answer text, questions, check details, errors, source paths, headings, case
identifiers, and run metadata are treated as untrusted display data. The
renderer validates the consumed fields, rejects invalid metric ranges and
inconsistent case counts, and HTML-escapes every report-derived string. It never
embeds the raw report in executable JavaScript. The prompt-injection case
deliberately demonstrates that adversarial text can reach evaluation evidence.

The dashboard remains backwards-compatible with the tracked
[`v1 schema`](../schemas/evaluation-report-v1.schema.json). Legacy reports omit
the question and expected behavior, so the renderer supplies an honest fallback
instead of inventing missing information.

Repeated performance and consistency evidence uses a separate
[benchmark contract and dashboard](BENCHMARKING.md). Keeping it separate avoids
pretending one evaluation run contains a latency distribution.

## Presentation and framework boundary

The tracked schema is the boundary between scoring and presentation. The local
dashboard reads the existing metrics without redefining them. DeepEval,
Ragas, or another framework may later contribute additional fields through a
new schema version, but it must not silently redefine the existing
human-labelled metrics.

Semantic faithfulness now uses a separate
[human-labelled validation contract](FAITHFULNESS.md). It compares a candidate
judge with audited labels and applies explicit acceptance thresholds without
redefining the RAG evaluation report's deterministic rubric. The original
grader remains `deterministic-rubric-v1`, and neither artifact claims complete
semantic entailment.
