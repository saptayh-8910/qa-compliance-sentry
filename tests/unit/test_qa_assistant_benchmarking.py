from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from qa_assistant.benchmarking import (
    BENCHMARK_REPORT_SCHEMA_VERSION,
    BenchmarkMetadata,
    BenchmarkReport,
    BenchmarkSample,
    benchmark_report_data,
    percentile,
    write_benchmark_report,
)
from qa_assistant.evaluation import (
    EvaluationCheck,
    EvaluationMetrics,
    EvaluationResult,
    ExpectedBehavior,
)
from qa_assistant.models import AnswerCitation, GroundedAnswer, RetrievalContext
from qa_assistant.openai_generator import ResponseUsage


def _result(
    case_id: str, passed: bool, answer_text: str | None = None
) -> EvaluationResult:
    answer = (
        GroundedAnswer(
            question=f"Question for {case_id}?",
            text=answer_text,
            citations=(),
            context=RetrievalContext("query", (), ""),
        )
        if answer_text is not None
        else None
    )
    return EvaluationResult(
        case_id=case_id,
        question=f"Question for {case_id}?",
        expected_behavior=ExpectedBehavior.SUPPORTED,
        answer=answer,
        metrics=EvaluationMetrics(1.0, 1.0, True, 1.0, 1.0, 1.0),
        checks=(EvaluationCheck("rubric", passed, "observable rubric result"),),
    )


def _report() -> BenchmarkReport:
    durations = (0.10, 0.20, 0.30)
    samples = tuple(
        BenchmarkSample(
            iteration=iteration,
            result=_result(
                case_id,
                passed,
                (
                    "same answer"
                    if case_id == "stable-pass"
                    else f"variant {iteration != 2}"
                    if case_id == "variable"
                    else None
                ),
            ),
            duration_seconds=durations[iteration - 1] + case_offset,
            usage=(
                ResponseUsage(10 * iteration, 5 * iteration, 15 * iteration, 2)
                if case_id == "stable-pass"
                else None
            ),
        )
        for iteration in range(1, 4)
        for case_id, passed, case_offset in (
            ("stable-pass", True, 0.0),
            ("stable-fail", False, 0.01),
            ("variable", iteration != 2, 0.02),
        )
    )
    return BenchmarkReport(
        metadata=BenchmarkMetadata(
            benchmark_id="benchmark-001",
            created_at=datetime(2026, 8, 12, 12, tzinfo=UTC),
            provider="scripted",
            model="reference-model",
            reasoning_effort="none",
            repetitions=3,
        ),
        samples=samples,
    )


def test_nearest_rank_percentile_matches_small_sample_boundaries() -> None:
    values = (0.4, 0.1, 0.3, 0.2)

    assert percentile(values, 0.5) == 0.2
    assert percentile(values, 0.95) == 0.4
    assert percentile(values, 1.0) == 0.4


@pytest.mark.parametrize(
    ("values", "rank", "message"),
    [
        ((), 0.5, "at least one"),
        ((1.0,), 0.0, "greater than 0"),
        ((1.0,), 1.1, "at most 1"),
        ((float("nan"),), 0.5, "finite"),
    ],
)
def test_percentile_rejects_invalid_inputs(
    values: tuple[float, ...], rank: float, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        percentile(values, rank)


def test_benchmark_separates_correctness_stability_latency_and_tokens() -> None:
    report = _report()
    summary = report.summary
    cases = {case.case_id: case for case in report.case_summaries}

    assert summary.case_count == 3
    assert summary.sample_count == 9
    assert summary.passed_sample_count == 5
    assert summary.sample_pass_rate == pytest.approx(5 / 9)
    assert summary.stable_case_count == 2
    assert summary.stability_rate == pytest.approx(2 / 3)
    assert summary.response_stable_case_count == 2
    assert summary.response_stability_rate == pytest.approx(2 / 3)
    assert summary.latency.p50_seconds == pytest.approx(0.21)
    assert summary.latency.p95_seconds == pytest.approx(0.32)
    assert summary.tokens is not None
    assert summary.tokens.sample_count == 3
    assert summary.tokens.total_tokens == 90
    assert summary.tokens.p50_total_tokens == 30
    assert summary.tokens.p95_total_tokens == 45
    assert cases["stable-pass"].verdict == "consistently-passed"
    assert cases["stable-fail"].verdict == "consistently-failed"
    assert cases["variable"].verdict == "variable"
    assert cases["variable"].answer_variant_count == 2
    assert cases["variable"].citation_variant_count == 1
    assert cases["variable"].response_stable is False
    assert cases["stable-fail"].stable is True
    assert cases["stable-fail"].pass_rate == 0
    assert cases["variable"].tokens is None


def test_benchmark_serialization_is_dashboard_ready() -> None:
    data = benchmark_report_data(_report())

    assert data["schema_version"] == BENCHMARK_REPORT_SCHEMA_VERSION == "1.0"
    assert data["run"]["repetitions"] == 3
    assert data["summary"]["sample_count"] == 9
    assert data["summary"]["stable_case_count"] == 2
    assert data["summary"]["response_stable_case_count"] == 2
    assert data["cases"][1]["verdict"] == "consistently-failed"
    assert data["cases"][2]["tokens"] is None


def test_response_consistency_compares_canonical_citation_sets() -> None:
    result = _result("citations", True, "same answer")
    citations = (
        AnswerCitation(1, "a.md", "A"),
        AnswerCitation(2, "b.md", "B"),
    )
    first = replace(result, answer=replace(result.answer, citations=citations))
    second = replace(
        result,
        answer=replace(result.answer, citations=tuple(reversed(citations))),
    )
    report = BenchmarkReport(
        BenchmarkMetadata("benchmark", datetime.now(UTC), "scripted", repetitions=2),
        (BenchmarkSample(1, first, 0.1), BenchmarkSample(2, second, 0.2)),
    )

    assert report.case_summaries[0].citation_variant_count == 1
    assert report.case_summaries[0].response_stable is True


def test_benchmark_writer_is_atomic_and_schema_is_tracked(tmp_path: Path) -> None:
    output = tmp_path / "nested" / "benchmark.json"
    write_benchmark_report(_report(), output)

    assert json.loads(output.read_text(encoding="utf-8")) == benchmark_report_data(
        _report()
    )
    assert output.read_text(encoding="utf-8").endswith("\n")
    assert tuple(output.parent.glob("*.tmp")) == ()

    schema_path = (
        Path(__file__).resolve().parents[2]
        / "schemas"
        / "benchmark-report-v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == "1.0"


@pytest.mark.parametrize(
    ("iteration", "duration", "usage", "message"),
    [
        (0, 0.1, None, "iteration"),
        (1, -0.1, None, "duration"),
        (1, 0.1, ResponseUsage(-1, 2, 1), "token counts"),
    ],
)
def test_benchmark_sample_rejects_invalid_telemetry(
    iteration: int,
    duration: float,
    usage: ResponseUsage | None,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        BenchmarkSample(iteration, _result("case", True), duration, usage)


def test_benchmark_report_rejects_missing_or_duplicate_iterations() -> None:
    metadata = BenchmarkMetadata(
        "benchmark", datetime.now(UTC), "scripted", repetitions=2
    )
    result = _result("case", True)

    with pytest.raises(ValueError, match="exactly 2 samples"):
        BenchmarkReport(metadata, (BenchmarkSample(1, result, 0.1),))
    with pytest.raises(ValueError, match="each iteration once"):
        BenchmarkReport(
            metadata,
            (BenchmarkSample(1, result, 0.1), BenchmarkSample(1, result, 0.2)),
        )
