"""Repeated-run latency and verdict-stability evidence for RAG evaluation."""

from __future__ import annotations

import json
import os
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil, isfinite
from pathlib import Path
from typing import Any

from qa_assistant.evaluation import EvaluationResult, ExpectedBehavior
from qa_assistant.openai_generator import ResponseUsage
from qa_assistant.reporting import DEFAULT_EVALUATION_DATASET, DETERMINISTIC_GRADER

BENCHMARK_REPORT_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True, slots=True)
class BenchmarkSample:
    """One case result from one numbered benchmark repetition."""

    iteration: int
    result: EvaluationResult
    duration_seconds: float
    usage: ResponseUsage | None = None

    def __post_init__(self) -> None:
        if isinstance(self.iteration, bool) or self.iteration < 1:
            raise ValueError("benchmark iteration must be at least 1")
        if not isfinite(self.duration_seconds) or self.duration_seconds < 0:
            raise ValueError("benchmark duration must be a finite non-negative number")
        if self.usage is not None:
            counts = (
                self.usage.input_tokens,
                self.usage.output_tokens,
                self.usage.total_tokens,
            )
            if any(count < 0 for count in counts):
                raise ValueError("benchmark token counts cannot be negative")
            if (
                self.usage.reasoning_tokens is not None
                and self.usage.reasoning_tokens < 0
            ):
                raise ValueError("benchmark reasoning tokens cannot be negative")


@dataclass(frozen=True, slots=True)
class BenchmarkMetadata:
    """Identity and execution configuration for one repeated benchmark."""

    benchmark_id: str
    created_at: datetime
    provider: str
    repetitions: int
    dataset: str = DEFAULT_EVALUATION_DATASET
    grader: str = DETERMINISTIC_GRADER
    model: str | None = None
    reasoning_effort: str | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("benchmark_id", self.benchmark_id),
            ("provider", self.provider),
            ("dataset", self.dataset),
            ("grader", self.grader),
        ):
            if not value.strip():
                raise ValueError(f"benchmark {name} cannot be empty")
        if isinstance(self.repetitions, bool) or self.repetitions < 2:
            raise ValueError("benchmark repetitions must be at least 2")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("benchmark created_at must include a timezone")
        if self.model is not None and not self.model.strip():
            raise ValueError("benchmark model cannot be empty")
        if self.reasoning_effort is not None and not self.reasoning_effort.strip():
            raise ValueError("benchmark reasoning_effort cannot be empty")


@dataclass(frozen=True, slots=True)
class LatencySummary:
    sample_count: int
    minimum_seconds: float
    p50_seconds: float
    p95_seconds: float
    maximum_seconds: float
    mean_seconds: float


@dataclass(frozen=True, slots=True)
class TokenSummary:
    sample_count: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_reasoning_tokens: int | None
    mean_total_tokens: float
    p50_total_tokens: float
    p95_total_tokens: float


@dataclass(frozen=True, slots=True)
class CaseBenchmarkSummary:
    case_id: str
    question: str
    expected_behavior: ExpectedBehavior
    sample_count: int
    passed_count: int
    pass_rate: float
    stable: bool
    answer_variant_count: int
    citation_variant_count: int
    response_stable: bool
    latency: LatencySummary
    tokens: TokenSummary | None

    @property
    def verdict(self) -> str:
        if not self.stable:
            return "variable"
        return "consistently-passed" if self.pass_rate == 1 else "consistently-failed"


@dataclass(frozen=True, slots=True)
class BenchmarkSummary:
    case_count: int
    sample_count: int
    passed_sample_count: int
    sample_pass_rate: float
    stable_case_count: int
    stability_rate: float
    response_stable_case_count: int
    response_stability_rate: float
    latency: LatencySummary
    tokens: TokenSummary | None


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    metadata: BenchmarkMetadata
    samples: tuple[BenchmarkSample, ...]

    def __post_init__(self) -> None:
        if not self.samples:
            raise ValueError("benchmark report requires at least one sample")
        grouped = _group_samples(self.samples)
        for case_id, samples in grouped.items():
            if len(samples) != self.metadata.repetitions:
                raise ValueError(
                    f"benchmark case {case_id!r} must have exactly "
                    f"{self.metadata.repetitions} samples"
                )
            iterations = {sample.iteration for sample in samples}
            expected = set(range(1, self.metadata.repetitions + 1))
            if iterations != expected:
                raise ValueError(
                    f"benchmark case {case_id!r} must contain each iteration once"
                )
            questions = {sample.result.question for sample in samples}
            behaviors = {sample.result.expected_behavior for sample in samples}
            if len(questions) != 1 or len(behaviors) != 1:
                raise ValueError(
                    f"benchmark case {case_id!r} changed its evaluation contract"
                )

    @property
    def case_summaries(self) -> tuple[CaseBenchmarkSummary, ...]:
        return tuple(
            _case_summary(case_id, samples)
            for case_id, samples in _group_samples(self.samples).items()
        )

    @property
    def summary(self) -> BenchmarkSummary:
        cases = self.case_summaries
        passed = sum(sample.result.passed for sample in self.samples)
        stable = sum(case.stable for case in cases)
        response_stable = sum(case.response_stable for case in cases)
        return BenchmarkSummary(
            case_count=len(cases),
            sample_count=len(self.samples),
            passed_sample_count=passed,
            sample_pass_rate=passed / len(self.samples),
            stable_case_count=stable,
            stability_rate=stable / len(cases),
            response_stable_case_count=response_stable,
            response_stability_rate=response_stable / len(cases),
            latency=_latency_summary(
                tuple(sample.duration_seconds for sample in self.samples)
            ),
            tokens=_token_summary(
                tuple(
                    sample.usage for sample in self.samples if sample.usage is not None
                )
            ),
        )


def _group_samples(
    samples: tuple[BenchmarkSample, ...],
) -> dict[str, tuple[BenchmarkSample, ...]]:
    grouped: defaultdict[str, list[BenchmarkSample]] = defaultdict(list)
    for sample in samples:
        grouped[sample.result.case_id].append(sample)
    return {case_id: tuple(values) for case_id, values in grouped.items()}


def percentile(values: tuple[float, ...], percentile_value: float) -> float:
    """Return the nearest-rank percentile for a non-empty finite sample."""
    if not values:
        raise ValueError("percentile requires at least one value")
    if not 0 < percentile_value <= 1:
        raise ValueError("percentile must be greater than 0 and at most 1")
    if any(not isfinite(value) for value in values):
        raise ValueError("percentile values must be finite")
    ordered = sorted(values)
    return ordered[ceil(percentile_value * len(ordered)) - 1]


def _latency_summary(values: tuple[float, ...]) -> LatencySummary:
    return LatencySummary(
        sample_count=len(values),
        minimum_seconds=min(values),
        p50_seconds=percentile(values, 0.50),
        p95_seconds=percentile(values, 0.95),
        maximum_seconds=max(values),
        mean_seconds=sum(values) / len(values),
    )


def _token_summary(usages: tuple[ResponseUsage, ...]) -> TokenSummary | None:
    if not usages:
        return None
    totals = tuple(float(usage.total_tokens) for usage in usages)
    reasoning = tuple(
        usage.reasoning_tokens for usage in usages if usage.reasoning_tokens is not None
    )
    return TokenSummary(
        sample_count=len(usages),
        total_input_tokens=sum(usage.input_tokens for usage in usages),
        total_output_tokens=sum(usage.output_tokens for usage in usages),
        total_tokens=sum(usage.total_tokens for usage in usages),
        total_reasoning_tokens=sum(reasoning) if reasoning else None,
        mean_total_tokens=sum(totals) / len(totals),
        p50_total_tokens=percentile(totals, 0.50),
        p95_total_tokens=percentile(totals, 0.95),
    )


def _case_summary(
    case_id: str, samples: tuple[BenchmarkSample, ...]
) -> CaseBenchmarkSummary:
    first = samples[0].result
    outcomes = tuple(sample.result.passed for sample in samples)
    answer_variants = {
        sample.result.answer.text if sample.result.answer is not None else None
        for sample in samples
    }
    citation_variants = {
        tuple(
            sorted(
                {
                    (citation.source, citation.heading)
                    for citation in sample.result.answer.citations
                }
            )
        )
        if sample.result.answer is not None
        else ()
        for sample in samples
    }
    usages = tuple(sample.usage for sample in samples if sample.usage is not None)
    return CaseBenchmarkSummary(
        case_id=case_id,
        question=first.question,
        expected_behavior=first.expected_behavior,
        sample_count=len(samples),
        passed_count=sum(outcomes),
        pass_rate=sum(outcomes) / len(outcomes),
        stable=len(set(outcomes)) == 1,
        answer_variant_count=len(answer_variants),
        citation_variant_count=len(citation_variants),
        response_stable=len(answer_variants) == len(citation_variants) == 1,
        latency=_latency_summary(tuple(sample.duration_seconds for sample in samples)),
        tokens=_token_summary(usages),
    )


def _latency_data(summary: LatencySummary) -> dict[str, int | float]:
    return {
        "sample_count": summary.sample_count,
        "minimum_seconds": summary.minimum_seconds,
        "p50_seconds": summary.p50_seconds,
        "p95_seconds": summary.p95_seconds,
        "maximum_seconds": summary.maximum_seconds,
        "mean_seconds": summary.mean_seconds,
    }


def _token_data(summary: TokenSummary | None) -> dict[str, int | float | None] | None:
    if summary is None:
        return None
    return {
        "sample_count": summary.sample_count,
        "total_input_tokens": summary.total_input_tokens,
        "total_output_tokens": summary.total_output_tokens,
        "total_tokens": summary.total_tokens,
        "total_reasoning_tokens": summary.total_reasoning_tokens,
        "mean_total_tokens": summary.mean_total_tokens,
        "p50_total_tokens": summary.p50_total_tokens,
        "p95_total_tokens": summary.p95_total_tokens,
    }


def _timestamp(value: datetime) -> str:
    return (
        value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )


def benchmark_report_data(report: BenchmarkReport) -> dict[str, Any]:
    """Return the public JSON-compatible repeated benchmark representation."""
    metadata = report.metadata
    summary = report.summary
    return {
        "schema_version": BENCHMARK_REPORT_SCHEMA_VERSION,
        "run": {
            "benchmark_id": metadata.benchmark_id,
            "created_at": _timestamp(metadata.created_at),
            "dataset": metadata.dataset,
            "grader": metadata.grader,
            "provider": metadata.provider,
            "model": metadata.model,
            "reasoning_effort": metadata.reasoning_effort,
            "repetitions": metadata.repetitions,
        },
        "summary": {
            "case_count": summary.case_count,
            "sample_count": summary.sample_count,
            "passed_sample_count": summary.passed_sample_count,
            "sample_pass_rate": summary.sample_pass_rate,
            "stable_case_count": summary.stable_case_count,
            "stability_rate": summary.stability_rate,
            "response_stable_case_count": summary.response_stable_case_count,
            "response_stability_rate": summary.response_stability_rate,
            "latency": _latency_data(summary.latency),
            "tokens": _token_data(summary.tokens),
        },
        "cases": [
            {
                "case_id": case.case_id,
                "question": case.question,
                "expected_behavior": case.expected_behavior.value,
                "sample_count": case.sample_count,
                "passed_count": case.passed_count,
                "pass_rate": case.pass_rate,
                "stable": case.stable,
                "verdict": case.verdict,
                "answer_variant_count": case.answer_variant_count,
                "citation_variant_count": case.citation_variant_count,
                "response_stable": case.response_stable,
                "latency": _latency_data(case.latency),
                "tokens": _token_data(case.tokens),
            }
            for case in report.case_summaries
        ],
    }


def write_benchmark_report(report: BenchmarkReport, output: Path) -> None:
    """Atomically write a formatted repeated benchmark report."""
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(
        benchmark_report_data(report), indent=2, sort_keys=True, allow_nan=False
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
