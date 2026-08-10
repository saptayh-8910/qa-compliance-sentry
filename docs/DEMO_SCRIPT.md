# Portfolio demo script

Use this script when recording your Loom/YouTube walkthrough. Paste the final URL into [README.md](../README.md).

## 0:00–0:30 — Bug Tracker CLI

```bash
source .venv/bin/activate
bug-tracker add "Checkout total mismatch" --severity high -d "Tax not applied"
bug-tracker list
bug-tracker search checkout
```

## 0:30–1:15 — E2E automation

```bash
pytest tests/e2e -m smoke -v --html=reports/e2e-report.html --self-contained-html
```

Show Sauce Demo flow in trace or headed mode (optional):

```bash
pytest tests/e2e -m smoke --headed --slowmo 500
```

## 1:15–1:45 — API & DB validation

```bash
pytest tests/api tests/db -v
python scripts/run_validations.py
```

## AI quality evaluation dashboard

```bash
make dashboard-rag
```

Open `reports/rag-dashboard.html`. Show the 50% offline baseline, filter to the
two failed cases, and expand their rubric checks. Explain that the failures are
intentional evidence: retrieval succeeds, while the extractive generator does
not yet resolve conflicting policies or remove a retrieved prompt injection.

Point out that the dashboard reads the same versioned JSON retained by CI,
escapes model-generated text, and makes no paid API request.

## Wrap-up

- Open `reports/report.html` if generated via `make report`
- Mention the progression from classic UI/API/DB automation through CI,
  reliability analysis, grounded RAG evaluation, and AI quality reporting.
