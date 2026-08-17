# Social media drafts for QA Compliance Sentry

These are shorter versions of the case study in [MEDIUM_ARTICLE.md](MEDIUM_ARTICLE.md). Update the repository or article link immediately before publishing.

## LinkedIn post

**A convincing AI answer is not proof of accuracy.**

I learned this while testing a small local model in my QA Compliance Sentry project.

The retriever ranked the expected OWASP requirement first. The model produced a reasonable answer, but it cited the wrong passages. If I had reviewed only the writing, I might have passed it. The evaluation showed citation precision and citation recall of 0%.

That is why I evolved this project from a traditional QA automation portfolio into an evidence-driven RAG quality workspace.

It now tests:

- retrieval quality, including Hit@K, context precision, context recall, and rank;
- citation precision and recall;
- answer faithfulness and safe abstention;
- prompt injection and conflicting evidence;
- latency, repeated-run stability, and model comparison;
- unit, integration, API, terminal, and Playwright browser workflows.

The current retriever is a custom BM25-style lexical baseline. It is not Hybrid or Graph RAG. That limitation is intentional and visible. The offline benchmark passes 5 of 10 labelled scenarios, and the failures tell me what to test next: paraphrase retrieval, multi-source synthesis, conflicting evidence, and unsafe context.

The biggest lesson was simple: retrieval success and generation success are not the same thing.

My next experiment will compare BM25, vector, and hybrid retrieval using the same labelled evidence and evaluation rules.

Project: https://github.com/saptayh-8910/qa-compliance-sentry

#QualityEngineering #AIQuality #RAG #SoftwareTesting #Python #Playwright #LLMEvaluation #SDET

---

## X / Threads post

I asked a local 1B model a question about OWASP ASVS.

Search ranked the correct requirement first. The answer sounded reasonable. But the model cited the wrong passages: 0% citation precision and 0% citation recall.

That is the core lesson behind QA Compliance Sentry: an AI answer is not evidence.

I built the project to separate retrieval quality from generation quality and test both with labelled cases, deterministic metrics, safety scenarios, model comparisons, and browser E2E tests.

It currently uses a BM25-style lexical baseline. It is not Hybrid or Graph RAG. Next I will compare BM25 with vector and hybrid retrieval using the same ground truth.

https://github.com/saptayh-8910/qa-compliance-sentry

#AIQuality #RAG #SoftwareTesting

---

## Six-part social thread

### 1/6

A convincing AI answer is not proof of accuracy.

In one QA Compliance Sentry test, search found the correct OWASP requirement, but a local model cited the wrong passages. The answer looked plausible; citation precision and recall were both 0%.

### 2/6

That result showed why RAG needs separate diagnostics:

- Did retrieval find the right evidence?
- Did generation use it correctly?
- Did the answer cite it?
- Were all claims supported?

One final pass/fail score cannot tell you where the system broke.

### 3/6

The project began with unit, API, database, and Playwright tests. It then grew through CI and failure intelligence into RAG evaluation: retrieval metrics, citations, faithfulness, prompt-injection cases, latency, stability, and model comparison.

### 4/6

The current retriever is a custom BM25-style lexical baseline. It is not Hybrid RAG or Graph RAG.

That simplicity gives me a fast, deterministic control group and makes failures easier to explain.

### 5/6

The offline benchmark passes 5/10 labelled scenarios. I keep the failures visible because they reveal the roadmap: paraphrase misses, conflicting evidence, multi-source synthesis, prompt injection, and unsafe unsupported context.

### 6/6

Next: compare BM25, vector, hybrid, and reranked retrieval against the same evidence labels. Add graph relationships only if cross-reference tests prove they help.

Project: https://github.com/saptayh-8910/qa-compliance-sentry

---

## Publishing rubric

Use this checklist before publishing the article or any derived post.

### Claims and evidence

- [ ] Every number still matches the repository version being linked.
- [ ] “Local milestone,” “offline baseline,” and “controlled test” are not presented as production-wide results.
- [ ] The 5/10 result remains visible; it is not replaced with only successful examples.
- [ ] Gemma timing and citation results are described as observations from a controlled run, not universal model performance.
- [ ] The project is called BM25-style lexical RAG, not Hybrid RAG or Graph RAG.

### Reader clarity

- [ ] Each technical metric includes a plain-English interpretation.
- [ ] The article explains the difference between retrieval and generation.
- [ ] Direct evidence, local AI, and paid cloud AI are clearly distinguished.
- [ ] Limitations appear before future claims.
- [ ] A non-technical reader can explain what a “good result” means after reading.

### Privacy and safety

- [ ] No private uploaded document, screenshot, secret, API key, or local `.env` value is included.
- [ ] Screenshots contain only public or synthetic test data.
- [ ] Local filesystem paths, terminal usernames, and browser tabs are cropped out where unnecessary.
- [ ] The text does not claim compliance certification or universal hallucination detection.

### Reproducibility

- [ ] The linked branch or release contains every feature and metric mentioned.
- [ ] Public setup instructions still work from a clean clone.
- [ ] Deterministic CI is passing.
- [ ] Optional paid and local-model tests are clearly labelled as opt-in.
- [ ] The GitHub link and any dashboard images open correctly.

### Recommended supporting images

1. The project architecture or roadmap.
2. The real-data workspace after loading OWASP ASVS.
3. One result showing evidence and verified citations.
4. The evaluation criteria cards with plain-English explanations.
5. A benchmark comparison that includes both successes and failures.
