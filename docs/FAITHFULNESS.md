# Human-labelled faithfulness validation

This Stage 4 milestone checks whether a candidate claim judge agrees with
human decisions before the project trusts that judge's scores. It is offline,
deterministic, free to run, and included in merge-blocking CI.

## What is being tested?

The judge receives one evidence passage and one claim. A human has already
assigned the correct label:

| Label | Plain-English meaning | Example |
|---|---|---|
| **Supported** | The evidence backs the claim. | Evidence says reports are kept for 30 days; the claim says the same. |
| **Contradicted** | The evidence directly conflicts with the claim. | Evidence says 30 days; the claim says 14 days. |
| **Unsupported** | The evidence does not tell us whether the claim is true. | Evidence discusses retention; the claim invents an encryption rule. |

Contradicted and unsupported claims are both considered **unfaithful** in the
binary safety measurements. They remain separate in the exact three-label
accuracy and confusion matrix because the failure causes are different.

The version-controlled dataset contains 15 human-labelled examples: five
supported, five contradicted, and five unsupported. Each example includes a
human explanation so a reviewer can audit why the label was chosen.

## Run it

```bash
make dashboard-faithfulness-rag

# Equivalent commands:
.venv/bin/qa-assistant faithfulness \
  --fail-if-unvalidated \
  --output reports/rag-faithfulness.json
.venv/bin/qa-assistant faithfulness-dashboard \
  --report reports/rag-faithfulness.json \
  --output reports/rag-faithfulness.html
```

The first command writes the versioned JSON evidence. The second renders a
standalone dashboard that works directly from disk and requires no remote
assets. `--fail-if-unvalidated` turns the acceptance policy into a CI gate.

## Evaluation criteria in plain English

All three acceptance conditions must pass:

| Measurement | Required result | How a non-technical reader should interpret it |
|---|---:|---|
| Exact label accuracy | at least 90% | At least 9 out of every 10 supported, contradicted, or unsupported labels must exactly match the humans. |
| Unfaithful recall | at least 95% | The judge must catch at least 95 out of every 100 contradicted or unsupported claims. Higher is safer. |
| False negatives | zero | No claim that a human marked contradicted or unsupported may be incorrectly accepted as supported in this dataset. |

The report also includes:

- **Unfaithful precision:** when the judge raises an alarm, how often the human
  also says the claim is contradicted or unsupported. Low precision means too
  many good claims are being blocked.
- **Unfaithful F1:** one combined number balancing unfaithful precision and
  recall. It is useful for comparison, but it does not replace the zero-false-
  negative safety rule.
- **Confusion matrix:** a count of every human label versus every judge label.
  It shows exactly which types of mistakes occurred.
- **False positive:** a human-supported claim that the judge blocks as
  contradicted or unsupported. This is inconvenient and can over-block users.
- **False negative:** a human-unfaithful claim that the judge accepts as
  supported. This is the more dangerous hallucination-control failure.

The current transparent baseline matches all 15 labels, so it records 100%
accuracy, precision, recall, and F1 with zero false negatives on this dataset.

## What the result does—and does not—prove

The candidate is a small lexical rule set. It recognizes the curated patterns,
including number conflicts, negation, before/after, include/exclude,
enabled/disabled, and strong token overlap. Its logic is intentionally visible
and testable.

“Validated” means only that this candidate passed the stated thresholds on
this small, version-controlled learning dataset. It does **not** prove universal
language understanding, production-grade semantic entailment, or performance
on unfamiliar domains. A future LLM or framework-based judge can implement the
same classifier boundary, but it must be compared with broader human labels
before its scores are trusted. The project does not use an unvalidated LLM as
the grading authority.

## Evidence contract and tamper resistance

[`schemas/faithfulness-report-v1.schema.json`](../schemas/faithfulness-report-v1.schema.json)
defines the public artifact. It records run identity, candidate name, policy,
aggregate metrics, the full three-by-three confusion matrix, and every claim,
human label, judge label, and human explanation.

Before rendering, the dashboard recalculates counts, accuracy, precision,
recall, F1, false positives, false negatives, and the confusion matrix from the
claim rows. It rejects inconsistent data and HTML-escapes every report-derived
string. Both JSON and HTML files are written atomically, so a reader sees a
complete prior file or a complete new file rather than a partial write.
