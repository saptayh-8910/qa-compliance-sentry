"""Versioned reporting for human-labelled faithfulness validation."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qa_assistant.faithfulness import FaithfulnessValidation

FAITHFULNESS_REPORT_SCHEMA_VERSION = "1.0"


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("faithfulness created_at must include a timezone")
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def faithfulness_report_data(
    validation: FaithfulnessValidation,
    *,
    run_id: str,
    created_at: datetime,
) -> dict[str, Any]:
    """Return the public JSON representation for one validation run."""
    if not run_id.strip():
        raise ValueError("faithfulness run_id cannot be empty")
    metrics = validation.metrics
    policy = validation.policy
    return {
        "schema_version": FAITHFULNESS_REPORT_SCHEMA_VERSION,
        "run": {
            "run_id": run_id,
            "created_at": _timestamp(created_at),
            "dataset": validation.dataset_name,
            "judge": validation.judge_name,
            "label_source": "human-authored-version-controlled",
        },
        "summary": {
            "validated": validation.validated,
            "example_count": metrics.example_count,
            "human_supported_count": metrics.human_supported_count,
            "human_faithfulness_rate": metrics.human_faithfulness_rate,
            "exact_match_count": metrics.exact_match_count,
            "accuracy": metrics.accuracy,
            "unfaithful_precision": metrics.unfaithful_precision,
            "unfaithful_recall": metrics.unfaithful_recall,
            "unfaithful_f1": metrics.unfaithful_f1,
            "false_positive_count": metrics.false_positive_count,
            "false_negative_count": metrics.false_negative_count,
            "confusion_matrix": metrics.confusion_matrix,
        },
        "policy": {
            "minimum_accuracy": policy.minimum_accuracy,
            "minimum_unfaithful_recall": policy.minimum_unfaithful_recall,
            "maximum_false_negatives": policy.maximum_false_negatives,
        },
        "claims": [
            {
                "claim_id": decision.example.identifier,
                "evidence": decision.example.evidence,
                "claim": decision.example.claim,
                "human_label": decision.example.human_label.value,
                "judge_label": decision.predicted_label.value,
                "correct": decision.correct,
                "human_explanation": decision.example.explanation,
            }
            for decision in validation.decisions
        ],
    }


def write_faithfulness_report(data: dict[str, Any], output: Path) -> None:
    """Atomically write formatted faithfulness evidence."""
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(data, indent=2, sort_keys=True, allow_nan=False)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(serialized)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        temporary_path.replace(output)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
