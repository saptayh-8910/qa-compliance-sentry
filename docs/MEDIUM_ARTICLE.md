# An AI Answer Is Not Evidence

## Building QA Compliance Sentry from classic test automation to evidence-driven RAG evaluation

During one of my first controlled tests with a small local AI model, the search system did something encouraging: it ranked the expected OWASP requirement first.

The model then produced a reasonable-sounding answer, but it cited the wrong retrieved passages.

If I had judged only the writing, I might have called the test successful. The evaluation results told a different story: citation precision was 0%, and citation recall was 0%.

That experiment captures the reason I built **QA Compliance Sentry**. A convincing AI answer is not proof that the system found the right evidence, used it correctly, or can repeat the result reliably.

This project began as a QA automation learning roadmap. It grew into a small, evidence-driven RAG quality laboratory where I can test retrieval, citations, faithfulness, latency, model behavior, and real browser workflows without hiding failures behind a polished chatbot response.

Repository: [github.com/saptayh-8910/qa-compliance-sentry](https://github.com/saptayh-8910/qa-compliance-sentry)

---

## Why I built one evolving project

I wanted to strengthen both fundamental and practical skills for an AI automation QA role. Instead of building unrelated mini-projects, I used one repository as a continuous learning environment.

The project evolved through four stages:

1. **Software testing foundations:** Python unit tests, API testing, SQLite persistence, Playwright browser automation, and algorithm practice.
2. **CI and failure intelligence:** Docker checks, compatibility testing, deterministic quality gates, failure clustering, and pipeline validation.
3. **Grounded RAG testing:** document retrieval, numbered citations, provider adapters, chatbot end-to-end tests, and safe refusal behavior.
4. **AI quality engineering:** labelled evaluation datasets, retrieval metrics, citation metrics, faithfulness checks, latency benchmarks, model comparison, and human-readable dashboards.

I also connected three LeetCode-style exercises to each stage. The goal was not to turn the project into an algorithm collection. It was to learn why data structures such as heaps, graphs, tries, caches, and sliding windows matter in real QA and retrieval systems.

The result is a portfolio project that shows how traditional software quality and AI quality fit together.

---

## What QA Compliance Sentry does

At its current milestone, a user can open a local browser workspace, upload supported text or Markdown documents, or load the official OWASP ASVS 5.0.0 dataset. The project converts those documents into searchable passages and lets the user ask questions against them.

The basic flow is:

```text
Documents or OWASP ASVS requirements
                |
                v
Structure-aware chunks with stable evidence IDs
                |
                v
Custom BM25-style lexical retrieval
                |
                v
Top-ranked, numbered evidence passages
                |
                v
Direct evidence | Local Gemma 3 1B | Cloud OpenAI
                |
                v
Citation validation and safety checks
                |
                v
Metrics, reports, dashboards, and regression results
```

The system does not simply display an answer. It also shows the retrieved evidence, verified citations, evaluation criteria, and a plain-English interpretation of every result.

For example, instead of showing only `Hit@K: Hit`, the dashboard explains that at least one expected source appeared in the first *K* search results. A non-technical reader should not need to know information-retrieval terminology to understand whether the system worked.

---

## Is this Hybrid RAG or Graph RAG?

No, not yet. That distinction matters.

The current retriever is a custom, in-memory **BM25-style lexical search system**. BM25 is a ranking method that rewards passages containing important query terms while reducing the influence of very common words. In plain English, it behaves like a more careful keyword search.

The project does **not** currently combine BM25 with dense vector embeddings. It also does not use a vector database, neural reranker, knowledge graph, or parent-document graph expansion. Therefore, I describe it as a lexical RAG and evaluation platform, not a Hybrid Graph RAG system.

This was a deliberate engineering decision. A simple deterministic retriever is inexpensive, fast, reproducible, and easy to debug. It gives me a measurable baseline before I add more complex components.

That baseline has already exposed an important weakness: lexical retrieval can miss paraphrases when the question and source use different words. A hybrid retriever may improve that case, but I want to prove the improvement against the same labelled dataset rather than assume that more architecture automatically means better quality.

A future comparison can test:

- BM25 alone;
- vector retrieval alone;
- BM25 plus vector retrieval;
- hybrid retrieval plus reranking;
- graph expansion only for questions that genuinely require cross-references.

The winning design should be selected by evidence: retrieval quality, faithfulness, latency, stability, cost, and operational complexity.

---

## Three answer modes, three different purposes

The browser workspace supports three answer strategies.

### 1. Direct evidence

This mode does not use a generative model. It returns the strongest retrieved passage with a verified citation.

It is the fastest and most deterministic option, usually completing in a few milliseconds in local tests. Its writing is less natural, but its behavior is easy to reproduce and audit.

### 2. Local Gemma 3 1B

This mode uses Gemma 3 1B through Ollama on my laptop. It has no per-question API charge and keeps inference local.

The model can make the response more conversational, but generation adds latency and another failure point. A small model can misunderstand instructions, select weak citations, or add unsupported details even when retrieval found the right source.

### 3. Cloud OpenAI

This optional mode supports cloud-model experiments. It is kept out of deterministic CI and requires explicit confirmation before a paid question is sent.

This separation lets me compare a deterministic baseline, a resource-constrained local model, and stronger cloud models without pretending they have the same cost or risk profile.

---

## The small-model experiment that changed how I judged the system

For a controlled ASVS question, the retriever placed the expected requirement at rank one. Gemma produced a concise and readable answer, but its structured citation selection pointed to other retrieved passages.

The system reported:

- the expected evidence was retrieved successfully;
- the model did not cite that evidence;
- citation precision was 0%;
- citation recall was 0%;
- the generated path was substantially slower than direct evidence.

This test separated two questions that are often incorrectly combined:

1. **Did search find the right information?** Yes.
2. **Did the model use and cite that information correctly?** No.

That distinction is central to RAG quality engineering. If the final answer receives only one pass/fail score, it is difficult to know whether to fix chunking, retrieval, prompting, model selection, or citation handling.

It also explains why a small local model can be slower than direct evidence. Direct evidence is a search-and-format operation. Local AI generation must load or warm a model, process a prompt, predict tokens one at a time, and then pass citation validation. “Local” and “small” do not mean “instant.”

---

## The metrics and what they mean to a human reader

The project treats evaluation criteria as part of the product, not an internal implementation detail.

| Metric | Technical question | Plain-English meaning |
| --- | --- | --- |
| Hit@K | Did any expected evidence appear in the first K results? | Did the search find at least one source we already know is relevant? |
| Context precision | How much retrieved context was relevant? | How much unnecessary material did search bring back? |
| Context recall | How much expected evidence was retrieved? | Did search find all the important sources, or leave some out? |
| Reciprocal rank | How high was the first relevant result? | Did the useful evidence appear near the top, where a model is more likely to use it? |
| Citation precision | How many returned citations were expected? | Did the answer point to relevant sources rather than unrelated ones? |
| Citation recall | How many expected citations were returned? | Did the answer cite all the sources it should have used? |
| Faithfulness | Are answer claims supported by cited context? | Did the model stay within the evidence instead of inventing extra claims? |
| Latency | How long did the request take? | How long did the user wait? |
| Stability | Did repeated runs stay within an allowed variance? | Can we expect similar performance next time? |

When ground-truth evidence IDs are not provided, the project reports some accuracy metrics as **not measured** rather than inventing a score. This is a small design choice, but an important one: uncertainty should remain visible.

---

## Applying the testing pyramid to an AI system

RAG evaluation does not replace traditional software testing. It adds another quality layer.

### Unit tests

Fast tests cover isolated behavior such as chunking, ranking, citation parsing, metric calculations, escaping, safety rules, and algorithms. External services are mocked or excluded.

### Integration tests

These verify boundaries between components: API routes and SQLite, retrieval and answer generation, report builders and saved artifacts, model adapters and fail-closed citation validation.

### End-to-end tests

Terminal and Playwright browser tests exercise workflows a real user follows: start the service, upload or load documents, ask a question, inspect evidence, and view evaluation results.

### Opt-in external tests

Real provider and local-model experiments are separated from deterministic CI. Network availability, API cost, model warm-up time, and provider changes should not make every pull request flaky.

At the current local milestone, the deterministic suite contains **385 tests** with **88.80% branch-aware coverage**, plus terminal and browser smoke coverage. The exact number is less important than the layering: fast checks provide frequent feedback, while fewer integration and end-to-end tests protect critical user journeys.

---

## A 50% baseline can be more useful than a perfect demo

The offline labelled RAG benchmark currently passes 5 of 10 scenarios.

That may not sound impressive, but it is more useful than selecting only easy questions and reporting 100%.

The failing cases identify concrete gaps:

- conflicting evidence;
- prompt-injection text inside retrieved documents;
- questions requiring multi-source synthesis;
- lexical paraphrase mismatches;
- unsafe or unsupported context.

Each failure points toward a different engineering action. Paraphrase misses may justify embeddings. Conflicting evidence may require source-priority rules or explicit contradiction handling. Multi-source questions may need retrieval diversification and a stronger synthesis model. Prompt injection requires treating retrieved content as untrusted data, not instructions.

The benchmark is therefore not only a scorecard. It is a debugging map and a roadmap.

---

## Testing with real compliance data

To move beyond synthetic fixtures, I added the official OWASP Application Security Verification Standard 5.0.0 dataset.

The local workspace can index **345 ASVS requirements** and run six human-labelled starter cases. Stable requirement IDs provide useful ground truth because I can state in advance which evidence should answer each question.

This makes the project a better QA demonstration, but it does not turn it into a compliance certification product. The dataset pilot proves that the workflow can ingest structured real-world material and produce measurable retrieval behavior. It does not prove coverage of every organization, policy type, language, or production workload.

Uploaded files are session-scoped and kept out of version control. That reduces accidental repository growth and avoids treating private test documents as permanent project assets.

---

## Safety and trust are testable behaviors

The project includes adversarial and safety-oriented cases because RAG systems can fail even when their infrastructure works correctly.

Examples include:

- retrieved text that tells the model to ignore instructions;
- questions whose answers are not supported by the documents;
- conflicting passages;
- fabricated or malformed citations;
- unsupported claims added to an otherwise correct answer;
- unsafe text rendered in an HTML report.

The answer pipeline validates citations against the retrieved evidence and fails closed when the response does not satisfy the contract. Reports escape untrusted content. Unsupported questions should abstain instead of producing a confident guess.

Faithfulness grading is also tested against a small human-labelled validation set. I present this as bounded evidence, not as proof that one rule detects every hallucination. If an LLM judge is added later, it should first be evaluated against human labels and monitored for false positives and false negatives.

---

## What this project proves and what it does not

QA Compliance Sentry demonstrates that I can:

- connect unit, integration, end-to-end, and AI-specific evaluation in one workflow;
- build and test a transparent BM25-style retriever;
- separate retrieval failures from generation failures;
- validate citations rather than trusting formatted model output;
- design labelled regression datasets and readable evaluation reports;
- compare deterministic, local, and cloud answer paths;
- integrate real public compliance data without hiding baseline failures;
- explain technical metrics in language a product owner or auditor can understand.

It does not yet demonstrate:

- a production-scale vector database;
- hybrid dense-and-sparse retrieval;
- graph-based legal or regulatory relationships;
- universal hallucination detection;
- production security certification;
- statistically broad model benchmarking;
- performance under large concurrent workloads.

Those limitations do not weaken the project. They define the boundary of the evidence and make the next experiments testable.

---

## What I learned

### A fluent answer can still fail

Readability is a user-experience property. Correct sourcing is a quality property. A strong system needs both, and they should be measured separately.

### Retrieval and generation need different diagnostics

If search found the correct evidence but the model cited something else, replacing the retriever would address the wrong problem.

### Deterministic baselines are valuable

Direct evidence is not as conversational, but it provides a fast control group. Without a control group, it is difficult to quantify what a model improves or breaks.

### More complex RAG should earn its complexity

Hybrid search, reranking, and graphs are promising tools. I want to add them as measured experiments, not architectural decorations.

### Honest failures make a stronger portfolio

A dashboard that explains why five cases failed shows more engineering judgment than a perfect score created from easy examples.

### AI quality is still software quality

Models add probabilistic behavior, but versioning, test isolation, CI gates, contracts, security checks, reproducibility, and clear failure reports remain essential.

---

## What comes next

My next major experiment is a controlled retrieval comparison using the same documents, questions, expected evidence IDs, and evaluation rules.

I plan to compare the current lexical baseline against vector and hybrid alternatives. If cross-reference questions justify a graph layer, I can add it as another experiment and measure whether the quality gain is worth the added complexity.

The goal is not to claim that one architecture is always best. The goal is to build a repeatable method for answering a more useful question:

> For this dataset and user need, which design produces the most relevant, faithful, stable, understandable, and cost-effective result?

That is how I now think about AI quality engineering. The model’s answer is only the visible output. The real product is the chain of evidence that lets us decide whether that answer deserves trust.

---

## Suggested publication tags

`Quality Engineering` · `AI Quality` · `RAG` · `Software Testing` · `Python` · `Playwright` · `LLM Evaluation` · `SDET`
