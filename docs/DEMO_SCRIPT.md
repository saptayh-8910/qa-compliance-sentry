# 2-minute demo script

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

## 1:45–2:00 — Wrap-up

- Open `reports/report.html` if generated via `make report`
- Mention Stage 2: Docker + GitHub Actions next
