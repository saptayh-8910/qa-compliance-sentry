from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from qa_assistant.benchmark_dashboard import (
    BenchmarkDashboardDataError,
    load_benchmark_report,
    render_benchmark_dashboard,
    validate_benchmark_report,
    write_benchmark_dashboard,
)


def _latency(sample_count: int) -> dict[str, object]:
    return {
        "sample_count": sample_count,
        "minimum_seconds": 0.01,
        "p50_seconds": 0.02,
        "p95_seconds": 0.04,
        "maximum_seconds": 0.04,
        "mean_seconds": 0.025,
    }


def _case(
    case_id: str,
    passed_count: int,
    stable: bool,
    verdict: str,
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "question": f"What should {case_id} do?",
        "expected_behavior": "supported",
        "sample_count": 3,
        "passed_count": passed_count,
        "pass_rate": passed_count / 3,
        "stable": stable,
        "verdict": verdict,
        "answer_variant_count": 2 if verdict == "variable" else 1,
        "citation_variant_count": 1,
        "response_stable": verdict != "variable",
        "latency": _latency(3),
        "tokens": None,
    }


def _report() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "run": {
            "benchmark_id": "benchmark-test",
            "created_at": "2026-08-12T01:00:00.000000Z",
            "dataset": "stage4-grounding-v2",
            "grader": "deterministic-rubric-v1",
            "provider": "extractive",
            "model": None,
            "reasoning_effort": None,
            "repetitions": 3,
        },
        "summary": {
            "case_count": 3,
            "sample_count": 9,
            "passed_sample_count": 5,
            "sample_pass_rate": 5 / 9,
            "stable_case_count": 2,
            "stability_rate": 2 / 3,
            "response_stable_case_count": 2,
            "response_stability_rate": 2 / 3,
            "latency": _latency(9),
            "tokens": None,
        },
        "cases": [
            _case("stable-pass", 3, True, "consistently-passed"),
            _case("stable-fail", 0, True, "consistently-failed"),
            _case("variable", 2, False, "variable"),
        ],
    }


def test_benchmark_dashboard_explains_every_evaluation_criterion() -> None:
    rendered = render_benchmark_dashboard(_report())

    assert "Is the result fast—and repeatable?" in rendered
    assert "Sample pass rate" in rendered
    assert "Verdict stability" in rendered
    assert "Response consistency" in rendered
    assert "Typical latency · p50" in rendered
    assert "Slower-end latency · p95" in rendered
    assert "Evaluation criteria" in rendered
    assert "Stable does not mean correct." in rendered
    assert "This learning baseline sets no production SLA." in rendered
    assert "Offline runs have no provider token bill." in rendered
    assert "The behavior is repeatable, but it is still wrong." in rendered
    assert 'data-verdict="variable"' in rendered
    assert "card.hidden=!show" in rendered


def test_benchmark_dashboard_escapes_untrusted_strings() -> None:
    report = _report()
    payload = '<script>alert("unsafe")</script>'
    report["run"]["provider"] = payload  # type: ignore[index]
    report["cases"][0]["case_id"] = payload  # type: ignore[index]
    report["cases"][0]["question"] = payload  # type: ignore[index]

    rendered = render_benchmark_dashboard(report)

    assert payload not in rendered
    assert rendered.count("&lt;script&gt;") == 3


def test_benchmark_dashboard_loads_and_writes_standalone_html(tmp_path: Path) -> None:
    source = tmp_path / "benchmark.json"
    output = tmp_path / "nested" / "benchmark.html"
    source.write_text(json.dumps(_report()), encoding="utf-8")

    loaded = load_benchmark_report(source)
    write_benchmark_dashboard(source, output)

    assert loaded["schema_version"] == "1.0"
    assert output.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert tuple(output.parent.glob("*.tmp")) == ()


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        ("schema_version", "2.0", "unsupported benchmark report"),
        ("summary.sample_count", 8, "multiplied by repetitions"),
        ("summary.stability_rate", 1.0, "does not match counts"),
        ("summary.response_stability_rate", 1.0, "does not match counts"),
        ("summary.latency.p50_seconds", 0.05, "percentiles must be ordered"),
        ("cases.1.verdict", "variable", "does not match its outcomes"),
        ("cases.2.response_stable", True, "does not match variant counts"),
    ],
)
def test_benchmark_dashboard_rejects_inconsistent_evidence(
    path: str, value: object, message: str
) -> None:
    report = deepcopy(_report())
    target: object = report
    parts = path.split(".")
    for part in parts[:-1]:
        target = target[int(part)] if part.isdigit() else target[part]  # type: ignore[index]
    target[parts[-1]] = value  # type: ignore[index]

    with pytest.raises(BenchmarkDashboardDataError, match=message):
        validate_benchmark_report(report)


def test_benchmark_dashboard_reports_invalid_json_location(tmp_path: Path) -> None:
    source = tmp_path / "invalid.json"
    source.write_text('{"schema_version":', encoding="utf-8")

    with pytest.raises(BenchmarkDashboardDataError, match=r"line 1, column 19"):
        load_benchmark_report(source)
