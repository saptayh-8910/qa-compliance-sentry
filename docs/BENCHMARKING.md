# Repeated latency and stability benchmarking

This Stage 4 milestone repeats the same versioned evaluation cases so one lucky
or unlucky result is not mistaken for a reliable system. The default path is
offline, deterministic, and free. It produces a JSON evidence contract and a
standalone dashboard without calling an external model.

## Run the baseline

```bash
make dashboard-benchmark-rag

# Equivalent commands:
.venv/bin/qa-assistant benchmark \
  --repetitions 3 \
  --output reports/rag-benchmark.json
.venv/bin/qa-assistant benchmark-dashboard \
  --report reports/rag-benchmark.json \
  --output reports/rag-benchmark.html
```

Three repetitions across ten cases produce 30 samples. Deterministic CI creates
and retains both files. It does not use an API key, network request, or paid
model.

## Evaluation criteria in plain English

| Measurement | What it asks | How to read it |
|---|---|---|
| Sample pass rate | Across every repeated case run, how many passed all retrieval, behavior, fact, safety, and citation checks? | 50% means half of the repeated samples met the complete rubric. |
| Verdict stability | Did a case keep the same pass/fail verdict on every repetition? | 100% means no case changed between passing and failing. It does not mean every case passed. |
| Response consistency | Did a case return the same exact answer text and canonical citation set every time? | 100% means no answer or verified-source variant appeared. This is stricter than verdict stability but still not semantic equivalence. |
| p50 latency | What completion time did at least half of the measured samples meet? | This is a useful description of a typical measured run. Lower is faster. |
| p95 latency | What completion time did at least 95% of the measured samples meet? | This describes the slower end of the sample. With only 30 samples, it is learning evidence rather than an SLA. |
| Token usage | How many input, output, total, and reasoning tokens did the provider report? | Offline results show N/A because no model tokens were purchased or consumed. |

Percentiles use the transparent nearest-rank method: sort the observations and
select the value at `ceil(percentile × sample count)`. This avoids interpolation
that could imply timing precision that was never observed.

## Why stability and correctness are separate

A case can be:

- **consistently passed:** every repetition passed;
- **consistently failed:** every repetition failed—the behavior is repeatable,
  but still wrong;
- **variable:** the pass/fail outcome changed between repetitions.

The benchmark also counts exact answer and citation variants. An external model
could pass every time but use different wording or sources, so a stable verdict
does not automatically mean a reproducible response.

The current extractive baseline is expected to pass 15 of 30 samples. All ten
cases keep the same verdict, answer text, and citations. That proves the offline
baseline is deterministic; it does not repair the five limitations already
identified by the quality dashboard.

## Paid-provider safety

An OpenAI benchmark requires both `--provider openai` and `--confirm-paid`.
Without the confirmation flag, the command exits before constructing the client
or making a request and prints the projected maximum number of calls. At three
repetitions, the ten-case dataset makes up to 24 paid generation calls because
two retrieval misses per repetition abstain before generation.

Paid benchmarking remains excluded from deterministic CI. A live experiment
should record its model, reasoning effort, repetition count, time window, and
pricing source. Token counts are retained; currency cost is not hard-coded
because model pricing can change.

## Contract and limitations

[`schemas/benchmark-report-v1.schema.json`](../schemas/benchmark-report-v1.schema.json)
defines the versioned artifact. The renderer validates counts, ranges,
percentile ordering, verdict consistency, response-variant consistency, and
untrusted strings before HTML-escaping report data.

This benchmark does not claim:

- a production latency service-level objective;
- statistically strong tail latency from only three repetitions;
- semantic equivalence between differently worded answers;
- cost estimates without a dated pricing source;
- model quality from speed or consistency alone.

The next Stage 4 boundary remains validated semantic faithfulness: any semantic
judge must first be compared against human labels before its scores are trusted.
