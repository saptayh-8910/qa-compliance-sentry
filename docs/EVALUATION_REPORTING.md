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
is intentionally diagnostic: supported evidence and retrieval-miss abstention
pass, while conflicting evidence and prompt injection expose limitations. The
command writes those failures and returns success so the report can be explored.
Use `--fail-on-failure` when the same rubric should act as a blocking gate.

Selecting `--provider openai` is explicit and makes three paid API requests for
the four-case dataset because the retrieval-miss case skips generation. Paid
runs are never enabled by deterministic CI.

## Generate the local dashboard

```bash
make dashboard-rag

# Or render an existing v1 report without re-running evaluation:
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

[`schemas/evaluation-report-v1.schema.json`](../schemas/evaluation-report-v1.schema.json)
is the public v1 contract. Each report contains:

- schema version plus run, dataset, grader, provider, model, and reasoning
  metadata;
- aggregate pass rate, context precision/recall, Hit@K, MRR, and citation
  precision/recall;
- per-case answer text, canonical citations, explainable checks, failure
  summary, and error;
- per-case duration and optional input, output, total, and reasoning token
  counts.

Non-applicable metrics remain JSON `null`. For example, Hit@K and reciprocal
rank do not apply when a case deliberately has no relevant evidence, and
citation precision/recall do not apply to a correct abstention. Converting these
values to zero would create misleading dashboard averages.

Reports are written through a temporary file in the destination directory and
atomically replaced. A reader therefore sees either the previous complete run
or the new complete run, never a partially written JSON document.

Answer text, check details, errors, source paths, headings, case identifiers,
and run metadata are treated as untrusted display data. The renderer validates
the consumed v1 fields, rejects invalid metric ranges and inconsistent case
counts, and HTML-escapes every report-derived string. It never embeds the raw
report in executable JavaScript. The prompt-injection case deliberately
demonstrates that adversarial text can reach evaluation evidence.

## Presentation and framework boundary

The tracked schema is the boundary between scoring and presentation. The local
dashboard reads the existing v1 metrics without redefining them. DeepEval,
Ragas, or another framework may later contribute additional fields through a
new schema version, but it must not silently redefine the existing
human-labelled metrics.

Any semantic faithfulness or LLM-as-judge score must first be compared with
human labels. Until that validation exists, the report identifies the grader as
`deterministic-rubric-v1` and does not claim complete semantic entailment.
