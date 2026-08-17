# Command reference

This page keeps detailed commands out of the main README. Run each command from
the project folder unless the page says otherwise.

## Install

You need Python 3.11 or newer and Git.

```bash
git clone https://github.com/saptayh-8910/qa-compliance-sentry.git
cd qa-compliance-sentry
make install
cp .env.example .env  # optional
```

`make install` creates a local Python environment, installs the project, and
downloads the Chromium browser used by Playwright.

## Open the RAG workspace

```bash
make workspace-rag
```

The page opens at `http://127.0.0.1:8765`. It runs only on your computer. Direct
evidence is the default answer mode and makes no AI request.

Read [REAL_WORLD_TESTING.md](REAL_WORLD_TESTING.md) for file limits, privacy
details, starter questions, and the meaning of each result.

## Use local Gemma

On macOS with Homebrew:

```bash
brew install ollama
brew services start ollama
ollama pull gemma3:1b
```

The workspace uses Gemma 3 1B by default. You can change the local settings in
`.env`:

```dotenv
OLLAMA_MODEL=gemma3:1b
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

The project accepts local Ollama addresses only. Local AI has no per-question
API fee, but it still uses your computer and takes more time than direct
evidence.

## Search and answer in the terminal

Search documents without writing an AI answer:

```bash
make retrieve-docs

.venv/bin/qa-assistant retrieve \
  "Why separate scheduled external checks from merge-blocking tests?" \
  --source docs --top 3
```

Return an answer from the best source passage:

```bash
make answer-docs

.venv/bin/qa-assistant answer \
  "Why separate scheduled external checks from merge-blocking tests?" \
  --source docs --top 3
```

Start a terminal chat that can accept several questions:

```bash
make chat-docs

.venv/bin/qa-assistant chat --source docs --top 3
```

Type `exit` or `quit` to stop the chat.

## Use paid OpenAI answers

Put the key only in your local `.env` file. Git ignores this file.

```dotenv
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-5.6-sol
OPENAI_REASONING_EFFORT=medium
```

The following command makes a paid outside request:

```bash
.venv/bin/qa-assistant answer \
  "Why separate scheduled external checks from merge-blocking tests?" \
  --source docs --top 3 --provider openai
```

You can choose a different model and reasoning level:

```bash
.venv/bin/qa-assistant answer \
  "Why separate scheduled external checks from merge-blocking tests?" \
  --source docs --provider openai \
  --model gpt-5.6-luna --reasoning-effort high
```

The project sends only the question, answer rules, and selected source passages.
It does not ask OpenAI to store the response. The answer must still pass the
same citation checks as the free mode.

## Create the RAG dashboard

```bash
make evaluate-rag
make dashboard-rag
```

The direct commands are:

```bash
.venv/bin/qa-assistant evaluate \
  --output reports/rag-evaluation.json

.venv/bin/qa-assistant dashboard \
  --report reports/rag-evaluation.json \
  --output reports/rag-dashboard.html
```

The offline test keeps five known failed cases. Add `--fail-on-failure` when a
failed case should make the command return an error.

## Test speed and repeated results

```bash
make benchmark-rag
make dashboard-benchmark-rag
```

The normal test runs ten cases three times. It records how many cases passed,
whether the results changed, and how long the tests took. It does not call an AI
model.

```bash
.venv/bin/qa-assistant benchmark \
  --repetitions 3 \
  --output reports/rag-benchmark.json
```

A cloud benchmark needs `--confirm-paid`. Three rounds can make 24 paid calls.
Read [BENCHMARKING.md](BENCHMARKING.md) before using that option.

## Test faithfulness rules

```bash
make faithfulness-rag
make dashboard-faithfulness-rag
```

This checks the project rule against 15 labels written by a person. It does not
prove that the rule can understand every possible sentence.

## Run software tests

| Command | What it runs |
| --- | --- |
| `make test-unit` | unit tests |
| `make test-algorithms` | 12 interview algorithms and QA examples |
| `make test-api` | public API tests |
| `make test-db` | local SQLite tests |
| `make test-e2e` | Sauce Demo browser test |
| `make test-chatbot-e2e` | terminal chatbot test with HTML and XML results |
| `make test-local` | unit, algorithm, and database tests without public services |
| `make test` | unit, algorithm, API, database, and browser tests |
| `make quality` | code style, formatting, coverage, and chatbot test |
| `make report` | the full pytest set with an HTML report |

The API and Sauce Demo tests need internet access.

## Run the paid model comparison

```bash
make test-ai-external
```

This compares Sol at medium reasoning with Luna at high reasoning. It uses four
test cases and makes six paid calls. It never runs during normal GitHub checks.
Read [MODEL_COMPARISON.md](MODEL_COMPARISON.md) before running it.

## Use the earlier QA tools

### Bug tracker

```bash
.venv/bin/bug-tracker add "Cart total incorrect" --severity high
.venv/bin/bug-tracker list
.venv/bin/bug-tracker search cart
.venv/bin/bug-tracker update <BUG_ID> --status in_progress
```

Bug data is stored in `data/bugs.json`.

### Test-log analysis

```bash
make analyze-sample

.venv/bin/log-analyzer analyze path/to/test-run.jsonl \
  --top 5 --incident-gap-seconds 300 \
  --output reports/log-analysis.json
```

### CI job checks

```bash
make validate-pipeline

.venv/bin/pipeline-validator validate path/to/pipeline.json
```

This command finds circular links that could stop CI jobs from running.

### Database checks

```bash
make validate
```

This creates the example SQLite database and runs read-only checks against it.

## Run with Docker

```bash
make docker-test      # build the image and run repeatable tests
make docker-quality   # run style, coverage, and report checks
make docker-external  # run public API and browser tests
```

The container runs as a user without administrator rights.

To use settings from `.env` with the outside tests:

```bash
make docker-external DOCKER_ENV_ARGS="--env-file .env"
```

## Create a Playwright HTML report

```bash
.venv/bin/pytest tests/e2e -m smoke \
  --html=reports/e2e-report.html --self-contained-html
```

Reports and failure screenshots are written under `reports/`. They are not
saved in Git.
