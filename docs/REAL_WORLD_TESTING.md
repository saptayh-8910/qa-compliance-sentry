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

No API key is required for the default direct-evidence mode. It deliberately
uses the deterministic extractive generator, so it makes no model request. It
removes UI boilerplate but does not rewrite the underlying source passage.

The optional **Local AI — no API fee** mode uses Gemma 3 1B through Ollama. It
runs the retrieved question and passages on this computer, with temperature
zero, a 4,096-token context, and a bounded answer. The model must still produce
valid numeric citations; local generation does not bypass the groundedness
contract. Because a small model can blend neighboring passages, the interface
also warns that a valid citation is not proof that every generated claim is
supported. Install it with `brew install ollama`, start it with
`brew services start ollama`, and download the model with
`ollama pull gemma3:1b`.

In the first controlled ASVS run on the project's 8 GB M1 test machine, Gemma
3 1B produced a concise answer in about 7.4 seconds. Retrieval ranked the
expected requirement first, but the model selected citations 2 and 3 instead
of expected citation 1. The workspace therefore reports failed citation
precision and recall for that run. This is one observation, not a universal
model benchmark, but it demonstrates why readable output and valid-looking
citations are evaluated separately.

The optional **Cloud AI — paid** mode uses the model and reasoning
effort configured in `.env`. The UI requires an explicit confirmation for each
question before it can make one paid request. It sends only the question,
grounding instructions, and retrieved passages through the existing OpenAI
adapter, disables response storage, validates numeric citations, and reports
token usage when the provider supplies it. Deterministic tests use a fake
generator and never make this request.

The page labels each mode explicitly. Direct evidence returns text from the
first retrieved passage. Local and cloud modes explain retrieved evidence in
plain English but differ in model size, privacy boundary, cost, and expected
quality. None of the modes reasons over passages that retrieval did not provide.
Broad overview requests receive a bounded retrieval adjustment that prefers
headings such as Overview, Introduction, Purpose, Problem, and Summary, or the
document's first section. Specific questions still use normal BM25 ranking.

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
| Response time | Retrieval and answering completed in the displayed time on this machine. |

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
- Plain-English AI can synthesize retrieved evidence, but a fluent answer can
  still be wrong; retrieval, citation, and human-labelled evaluation remain
  necessary.
- Overview-aware ranking handles a small class of introductory questions; it is
  not general semantic understanding.
- Expected IDs test retrieval and citations, not full semantic correctness.
- The system does not replace an application-security reviewer.
- A stronger case study should add 60–100 independently reviewed questions,
  preserve an untouched test split, report every failure, and measure agreement
  between at least two human reviewers on critical cases.
