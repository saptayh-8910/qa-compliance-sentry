# Real-world document testing

## Purpose

The browser workspace turns the project from a fixed demonstration into a
small local test bench. A user can index the pinned OWASP ASVS 5.0.0 source,
add Markdown or text files, ask questions, inspect retrieved evidence, and add
known evidence identifiers when an accuracy score is needed.

This is a real public-data pilot. It proves that the ingestion, retrieval,
citation, and diagnostic paths work on an external industry standard. It does
not by itself prove production adoption, universal question answering, or
fitness for every security decision.

## Start the workspace

Install the project once with `make install`, then run:

```bash
make workspace-rag
```

The command starts a local server at `http://127.0.0.1:8765` and opens it in the
default browser. It binds only to localhost. Press `Ctrl+C` in the terminal to
stop it.

No API key is required. The workspace deliberately uses the deterministic
extractive generator, so it makes no paid OpenAI calls.

The page labels that mode explicitly. It returns text from the first retrieved
passage; it does not combine multiple passages or reason over the complete
document. Broad overview requests receive a bounded retrieval adjustment that
prefers headings such as Overview, Introduction, Purpose, Problem, and Summary,
or the document's first section. Specific questions still use normal BM25
ranking.

## First ASVS test

1. Leave **OWASP Application Security Verification Standard 5.0.0** checked.
2. Press **Start testing**. The status should report 345 searchable chunks.
3. Select the SQL-injection starter question.
4. Confirm that the expected ID is `v5.0.0-1.2.4`.
5. Press **Ask question**.

A successful run should put that requirement in the retrieved results. Hit@K
will say **Hit**, context recall will say **100%**, and reciprocal rank will be
**1.00** when the expected requirement is the first result. Citation precision
and recall describe whether the answer cited the expected evidence.

The exact response time will vary by machine. One local timing is useful for
debugging but is not a production latency guarantee.

## Upload a local document

1. Press **Add your documents** and select up to 20 `.md` or `.txt` files.
   Official OWASP ASVS JSON is also supported.
2. Uncheck the public ASVS source if the test should use only the uploaded
   files.
3. Press **Start testing** again to create a new in-memory index.
4. Ask a question whose answer appears in those files.

Uploaded text is sent only to the localhost process, held in memory, and not
written to the project. The current limits are 5 MB total and 20 files per
indexing session. PDF, DOCX, arbitrary JSON, and scanned images are not yet
supported.

## Why expected evidence matters

The system cannot determine retrieval accuracy from a question alone. Someone
must first label which source passages are correct. The optional **Expected
evidence IDs** field supplies that ground truth.

For ASVS, enter one or more comma-separated versioned identifiers, for example:

```text
v5.0.0-6.4.3, v5.0.0-7.4.3
```

For ordinary uploaded Markdown or text, the workspace can answer and show
retrieved passages, but it does not yet provide an interface for assigning
stable passage IDs. Its accuracy metrics therefore remain **Not measured**.
This is intentional: a plausible answer is not automatically a correct answer.

## Metric guide

| Metric | Passing evidence in plain English |
|---|---|
| Hit@K | At least one expected passage appeared in the first K results. |
| Context precision | A high share of retrieved passages matched expected IDs. |
| Context recall | The search found all evidence IDs the label said were needed. |
| Reciprocal rank | The first correct passage appeared near the top; 1.00 means first place. |
| Citation precision | The answer did not cite unrelated retrieved passages. |
| Citation recall | The answer cited every expected evidence ID. |
| Local response time | Retrieval and extractive answering completed in the displayed time on this machine. |

Each result card repeats its criterion and explains the observed value for a
non-technical reader.

## Source integrity and license

The included file is the unmodified English JSON from the official stable
OWASP ASVS `v5.0.0_release` tag. Before indexing it, the workspace compares the
file to the SHA-256 checksum recorded in `data/library/catalog.json`. A mismatch
stops the run instead of silently testing altered data.

OWASP ASVS content is available under Creative Commons Attribution-ShareAlike
4.0. The local library README records the project link, stable release,
attribution, transformation, and license. OWASP does not endorse this project.

## Honest limits

- The six starter cases are a learning seed, not comprehensive ASVS coverage.
- The extractive baseline quotes the best passage; it does not synthesize a
  professional security assessment.
- Overview-aware ranking handles a small class of introductory questions; it is
  not general semantic understanding.
- Expected IDs test retrieval and citations, not full semantic correctness.
- The system does not replace an application-security reviewer.
- A stronger case study should add 60–100 independently reviewed questions,
  preserve an untouched test split, report every failure, and measure agreement
  between at least two human reviewers on critical cases.
