# QA Compliance Sentry v0.13.0

`v0.13.0` completes the four-stage Manual-to-AI Tester portfolio roadmap. The
project now connects traditional software quality gates with grounded RAG
evaluation, repeated AI stability evidence, and human-labelled faithfulness
validation.

## Highlights

- Python CLI, REST API, SQLite, and Playwright test foundations
- deterministic GitHub Actions across Python 3.11–3.14
- pinned non-root Playwright container workflow
- failure-log analysis and CI dependency-cycle detection
- twelve interview algorithm labs mapped to practical QA features
- citation-aware document retrieval and grounded answer orchestration
- explicit offline and OpenAI provider boundaries with safe abstention
- ten-case RAG evaluation spanning retrieval, generation, citations, prompt
  injection, conflicts, stale policy, and unsupported requests
- versioned evaluation, benchmark, and faithfulness JSON contracts
- standalone dashboards with always-visible plain-English evaluation criteria
- repeated p50/p95 latency, verdict stability, and exact response consistency
- 15 balanced human-labelled faithfulness claims with explicit safety gates

## Verified baseline

- 342 deterministic tests passed
- 92.34% branch-aware coverage
- chatbot E2E journey passed
- offline RAG evaluation: 5 of 10 cases pass, with five known diagnostic
  failures retained visibly
- offline repeated benchmark: 15 of 30 samples pass; all ten case verdicts and
  exact responses remain stable
- bounded faithfulness validation: 15 of 15 exact labels, 100% unfaithful
  recall, and zero false negatives

## Important limits

This is portfolio and learning evidence, not a production compliance
certification. The RAG and faithfulness datasets are deliberately small. Local
latency is not an SLA. Exact response consistency is not semantic equivalence.
The deterministic claim judge passing 15 examples does not establish universal
language understanding. External model tests are paid, opt-in experiments and
do not block normal CI.

## Run the evidence locally

```bash
make install
make quality
make dashboard-rag
make dashboard-benchmark-rag
make dashboard-faithfulness-rag
```

The generated reports are written under `reports/` and are intentionally not
committed. GitHub Actions retains equivalent deterministic evidence as a
workflow artifact.

## Portfolio entry points

- [Project overview](../README.md)
- [Project history](PROJECT_HISTORY.md)
- [Demo script](DEMO_SCRIPT.md)
- [RAG architecture and evaluation](RAG_ARCHITECTURE.md)
- [Benchmark methodology](BENCHMARKING.md)
- [Faithfulness methodology](FAITHFULNESS.md)
- [Algorithm learning track](ALGORITHM_LEARNING.md)
