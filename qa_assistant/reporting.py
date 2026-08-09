"""Versioned, dashboard-ready serialization for RAG evaluation evidence."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qa_assistant.evaluation import (
    EvaluationResult,
    EvaluationSummary,
    summarize_results,
)
from qa_assistant.openai_generator import ResponseUsage

EVALUATION_REPORT_SCHEMA_VERSION = "1.0"
DEFAULT_EVALUATION_DATASET = "stage3-grounding-v1"
DETERMINISTIC_GRADER = "deterministic-rubric-v1"


@dataclass(frozen=True, slots=True)
class EvaluationObservation:
    """One scored case plus optional runtime and token telemetry."""

    result: EvaluationResult
    duration_seconds: float
    usage: ResponseUsage | None = None

    def __post_init__(self) -> None:
        if self.duration_seconds < 0:
            raise ValueError("evaluation duration cannot be negative")
        if self.usage is not None:
            token_counts = (
                self.usage.input_tokens,
                self.usage.output_tokens,
                self.usage.total_tokens,
            )
            if any(count < 0 for count in token_counts):
                raise ValueError("evaluation token counts cannot be negative")
            if self.usage.reasoning_tokens is not None and (
                self.usage.reasoning_tokens < 0
            ):
                raise ValueError("evaluation reasoning tokens cannot be negative")


@dataclass(frozen=True, slots=True)
class EvaluationRunMetadata:
    """Identity and execution configuration for one evaluation run."""

    run_id: str
    created_at: datetime
    provider: str
    dataset: str = DEFAULT_EVALUATION_DATASET
    grader: str = DETERMINISTIC_GRADER
    model: str | None = None
    reasoning_effort: str | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("run_id", self.run_id),
            ("provider", self.provider),
            ("dataset", self.dataset),
            ("grader", self.grader),
        ):
            if not value.strip():
                raise ValueError(f"evaluation {name} cannot be empty")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("evaluation created_at must include a timezone")
        if self.model is not None and not self.model.strip():
            raise ValueError("evaluation model cannot be empty")
        if self.reasoning_effort is not None and not self.reasoning_effort.strip():
            raise ValueError("evaluation reasoning_effort cannot be empty")


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """One versioned evaluation run ready for JSON serialization."""

    metadata: EvaluationRunMetadata
    observations: tuple[EvaluationObservation, ...]

    def __post_init__(self) -> None:
        if not self.observations:
            raise ValueError("evaluation report requires at least one observation")
        case_ids = tuple(
            observation.result.case_id for observation in self.observations
        )
        if len(set(case_ids)) != len(case_ids):
            raise ValueError("evaluation report case identifiers must be unique")

    @property
    def summary(self) -> EvaluationSummary:
        return summarize_results(
            tuple(observation.result for observation in self.observations)
        )


def _utc_timestamp(value: datetime) -> str:
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def _summary_data(summary: EvaluationSummary) -> dict[str, int | float | None]:
    return {
        "case_count": summary.case_count,
        "passed_count": summary.passed_count,
        "pass_rate": summary.pass_rate,
        "mean_context_precision": summary.mean_context_precision,
        "mean_context_recall": summary.mean_context_recall,
        "hit_rate_at_k": summary.hit_rate_at_k,
        "mean_reciprocal_rank": summary.mean_reciprocal_rank,
        "mean_citation_precision": summary.mean_citation_precision,
        "mean_citation_recall": summary.mean_citation_recall,
    }


def _usage_data(usage: ResponseUsage | None) -> dict[str, int | None] | None:
    if usage is None:
        return None
    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.total_tokens,
        "reasoning_tokens": usage.reasoning_tokens,
    }


def _observation_data(observation: EvaluationObservation) -> dict[str, Any]:
    result = observation.result
    answer = result.answer
    return {
        "case_id": result.case_id,
        "passed": result.passed,
        "failure_summary": result.failure_summary,
        "error": result.error,
        "answer": (
            {
                "text": answer.text,
                "citations": [
                    {
                        "identifier": citation.identifier,
                        "source": citation.source,
                        "heading": citation.heading,
                    }
                    for citation in answer.citations
                ],
            }
            if answer is not None
            else None
        ),
        "metrics": {
            "context_precision": result.metrics.context_precision,
            "context_recall": result.metrics.context_recall,
            "hit_at_k": result.metrics.hit_at_k,
            "reciprocal_rank": result.metrics.reciprocal_rank,
            "citation_precision": result.metrics.citation_precision,
            "citation_recall": result.metrics.citation_recall,
        },
        "checks": [
            {
                "name": check.name,
                "passed": check.passed,
                "detail": check.detail,
            }
            for check in result.checks
        ],
        "telemetry": {
            "duration_seconds": observation.duration_seconds,
            "usage": _usage_data(observation.usage),
        },
    }


def evaluation_report_data(report: EvaluationReport) -> dict[str, Any]:
    """Return the public JSON-compatible v1 report representation."""
    metadata = report.metadata
    return {
        "schema_version": EVALUATION_REPORT_SCHEMA_VERSION,
        "run": {
            "run_id": metadata.run_id,
            "created_at": _utc_timestamp(metadata.created_at),
            "dataset": metadata.dataset,
            "grader": metadata.grader,
            "provider": metadata.provider,
            "model": metadata.model,
            "reasoning_effort": metadata.reasoning_effort,
        },
        "summary": _summary_data(report.summary),
        "cases": [
            _observation_data(observation) for observation in report.observations
        ],
    }


def write_evaluation_report(report: EvaluationReport, output: Path) -> None:
    """Atomically write a formatted JSON evaluation report."""
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(
        evaluation_report_data(report),
        indent=2,
        sort_keys=True,
        allow_nan=False,
    )
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
