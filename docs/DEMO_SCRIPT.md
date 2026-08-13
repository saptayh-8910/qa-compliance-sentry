# Portfolio demo script

This five-minute walkthrough emphasizes the engineering decisions and quality
evidence rather than trying to show every command.

## 0:00–0:30 — Problem and progression

Open [README.md](../README.md).

Say: “I built one project that grows from traditional QA automation into AI
quality engineering. It tests UI, API, database, CI, RAG retrieval, citations,
safety, stability, latency, and claim faithfulness.”

Point to the four completed roadmap stages and the AI Quality Engineering
table.

## 0:30–1:10 — Traditional testing pyramid

```bash
make quality
```

Explain:

- unit tests isolate logic and fail quickly;
- API and database tests verify boundaries and state;
- Playwright and the chatbot subprocess cover a few critical user journeys;
- deterministic checks block merges while external network/model tests remain
  scheduled or opt-in.

Use the verified baseline: 342 deterministic tests, 92.34% branch-aware
coverage, and one deterministic chatbot E2E journey.

## 1:10–2:20 — RAG quality diagnosis

```bash
make dashboard-rag
```

Open `reports/rag-dashboard.html`.

- Show the always-visible evaluation criteria.
- Explain Hit@K as: “Did the needed evidence appear anywhere in the retrieved
  results?”
- Explain context recall as: “How much of the needed evidence did retrieval
  find?”
- Explain citation precision as: “Of the sources cited, how many were correct?”
- Filter one passing and one failed case.

The offline baseline passes 5 of 10 cases. The five failures diagnose conflict
handling, prompt injection, multi-source synthesis, lexical paraphrase recall,
and unsafe context. Say explicitly that visible failures are more useful than a
misleading all-green dashboard.

## 2:20–3:10 — Stability and latency

```bash
make dashboard-benchmark-rag
```

Open `reports/rag-benchmark.html`.

Explain:

- correctness asks whether the full quality rubric passed;
- verdict stability asks whether pass/fail changed across repetitions;
- exact response consistency asks whether answer text and citations changed;
- p50 is the typical measured run and p95 represents the slower end.

The baseline is fully repeatable but still passes only 15 of 30 samples. A
stable failure remains wrong. Three local repetitions are learning evidence,
not a production SLA.

## 3:10–4:00 — Human-validated faithfulness

```bash
make dashboard-faithfulness-rag
```

Open `reports/rag-faithfulness.html`.

Show the three labels: supported, contradicted, and unsupported. Explain that
the candidate judge must achieve at least 90% exact accuracy, at least 95%
recall of unfaithful claims, and zero false negatives. A false negative means a
human-unfaithful claim was dangerously accepted as supported.

The baseline matches 15 of 15 curated labels. State the scope: this validates a
transparent rule set on a small audited dataset; it does not prove universal
semantic understanding.

## 4:00–4:35 — Engineering controls

Show `.github/workflows/ci.yml`, the versioned schemas under `schemas/`, and the
history in [PROJECT_HISTORY.md](PROJECT_HISTORY.md).

Mention:

- report writers use atomic replacement;
- dashboard renderers validate internal consistency and escape untrusted text;
- paid model calls require explicit opt-in and do not run in deterministic CI;
- pull requests retain the reason, diff, discussion, and CI evidence after
  branches are deleted.

## 4:35–5:00 — Close

Say: “The project’s value is not that every AI test is green. It shows that I
can design a layered quality strategy, isolate why an AI system failed, turn
technical metrics into plain English, and communicate the limits of the
evidence.”

End on [PORTFOLIO_HANDOFF.md](PORTFOLIO_HANDOFF.md) or the GitHub release page.
