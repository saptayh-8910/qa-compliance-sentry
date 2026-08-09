# Stage 4 evaluation reporting

Stage 4 begins by separating evaluation evidence from the tool that will
eventually visualize or extend it. The repository exports every deterministic
RAG result as a versioned JSON document so a dashboard, notebook, CI gate, or
future evaluation framework can consume the same facts without re-running a
model.

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

Answer text, check details, errors, source paths, and headings must be treated as
untrusted display data. A dashboard must escape these values instead of
inserting them as raw HTML; the prompt-injection case deliberately demonstrates
that adversarial text can reach evaluation evidence.

## Dashboard and framework boundary

The tracked schema is the boundary between scoring and presentation. The next
dashboard milestone can plot pass rate and metric trends directly from v1
reports. DeepEval, Ragas, or another framework may later contribute additional
fields through a new schema version, but it must not silently redefine the
existing human-labelled metrics.

Any semantic faithfulness or LLM-as-judge score must first be compared with
human labels. Until that validation exists, the report identifies the grader as
`deterministic-rubric-v1` and does not claim complete semantic entailment.
