from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from qa_assistant.dashboard import (
    DashboardDataError,
    load_dashboard_report,
    render_dashboard,
    validate_dashboard_report,
    write_dashboard,
)


def _report() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "run": {
            "run_id": "run-test",
            "created_at": "2026-08-09T12:00:00.000000Z",
            "dataset": "stage3-grounding-v1",
            "grader": "deterministic-rubric-v1",
            "provider": "extractive",
            "model": None,
            "reasoning_effort": None,
        },
        "summary": {
            "case_count": 1,
            "passed_count": 1,
            "pass_rate": 1.0,
            "mean_context_precision": 0.75,
            "mean_context_recall": 1.0,
            "hit_rate_at_k": 1.0,
            "mean_reciprocal_rank": 0.5,
            "mean_citation_precision": 1.0,
            "mean_citation_recall": None,
        },
        "cases": [
            {
                "case_id": "supported-case",
                "passed": True,
                "failure_summary": "all evaluation checks passed",
                "error": None,
                "answer": {
                    "text": "Coverage runs before merge [1].",
                    "citations": [
                        {
                            "identifier": 1,
                            "source": "quality-guide.md",
                            "heading": "Merge checks",
                        }
                    ],
                },
                "metrics": {
                    "context_precision": 0.75,
                    "context_recall": 1.0,
                    "hit_at_k": True,
                    "reciprocal_rank": 0.5,
                    "citation_precision": 1.0,
                    "citation_recall": None,
                },
                "checks": [
                    {
                        "name": "behavior",
                        "passed": True,
                        "detail": "expected supported; got supported",
                    }
                ],
                "telemetry": {
                    "duration_seconds": 0.0125,
                    "usage": None,
                },
            }
        ],
    }


def test_dashboard_renders_summary_cases_filters_and_not_applicable_metrics() -> None:
    rendered = render_dashboard(_report())

    assert "Grounded RAG quality, made visible." in rendered
    assert "100%" in rendered
    assert "supported-case" in rendered
    assert "quality-guide.md" in rendered
    assert "12.50</strong> ms" in rendered
    assert "N/A" in rendered
    assert 'data-filter="failed"' in rendered
    assert 'data-status="passed"' in rendered
    assert "card.hidden = !show" in rendered
    assert "How to read this evaluation" in rendered
    assert "Of everything retrieved, how much was actually useful?" in rendered
    assert "Needed evidence appeared in the retrieved results." in rendered
    assert "The first useful result appeared around position 2." in rendered
    assert "Every check below must pass for this case to pass." in rendered
    assert "<details>" not in rendered


def test_dashboard_explains_miss_and_not_applicable_without_jargon() -> None:
    report = _report()
    case = report["cases"][0]  # type: ignore[index]
    case["metrics"]["hit_at_k"] = False  # type: ignore[index]

    missed = render_dashboard(report)

    assert "Needed evidence did not appear in the retrieved results." in missed

    case["metrics"]["hit_at_k"] = None  # type: ignore[index]
    not_applicable = render_dashboard(report)

    assert "No supporting evidence was expected, so this does not apply." in (
        not_applicable
    )
    assert "it does not mean the scenario failed" in not_applicable


def test_dashboard_escapes_all_untrusted_display_fields() -> None:
    report = _report()
    case = report["cases"][0]  # type: ignore[index]
    payload = '<script>alert("unsafe")</script>'
    case["case_id"] = payload
    case["answer"]["text"] = payload  # type: ignore[index]
    case["answer"]["citations"][0]["source"] = payload  # type: ignore[index]
    case["checks"][0]["detail"] = payload  # type: ignore[index]

    rendered = render_dashboard(report)

    assert payload not in rendered
    assert "&lt;script&gt;alert(&quot;unsafe&quot;)&lt;/script&gt;" in rendered
    assert rendered.count("&lt;script&gt;") == 4


def test_dashboard_loads_json_and_writes_standalone_html(tmp_path: Path) -> None:
    source = tmp_path / "evaluation.json"
    output = tmp_path / "nested" / "dashboard.html"
    source.write_text(json.dumps(_report()), encoding="utf-8")

    loaded = load_dashboard_report(source)
    write_dashboard(source, output)

    assert loaded["schema_version"] == "1.0"
    assert output.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert tuple(output.parent.glob("*.tmp")) == ()


def test_dashboard_writer_removes_temporary_file_when_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "evaluation.json"
    output = tmp_path / "dashboard.html"
    source.write_text(json.dumps(_report()), encoding="utf-8")

    def fail_replace(source_path: Path, destination: Path) -> None:
        raise OSError(f"cannot replace {destination} from {source_path.name}")

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(OSError, match="cannot replace"):
        write_dashboard(source, output)

    assert not output.exists()
    assert tuple(path for path in tmp_path.iterdir() if path.suffix == ".tmp") == ()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (("schema_version", "2.0"), "unsupported evaluation report"),
        (("summary.pass_rate", 1.1), "summary.pass_rate must be between"),
        (("summary.pass_rate", True), "summary.pass_rate must be a number"),
        (("summary.mean_citation_recall", float("nan")), "must be finite"),
        (("summary.case_count", 2), "case_count does not match"),
        (("summary.passed_count", 0), "passed_count does not match"),
    ],
)
def test_dashboard_rejects_invalid_report_values(
    mutation: tuple[str, object], message: str
) -> None:
    report = deepcopy(_report())
    path, value = mutation
    target: dict[str, object] = report
    parts = path.split(".")
    for part in parts[:-1]:
        target = target[part]  # type: ignore[assignment]
    target[parts[-1]] = value

    with pytest.raises(DashboardDataError, match=message):
        validate_dashboard_report(report)


def test_dashboard_reports_invalid_json_location(tmp_path: Path) -> None:
    source = tmp_path / "invalid.json"
    source.write_text('{"schema_version":', encoding="utf-8")

    with pytest.raises(DashboardDataError, match=r"line 1, column 19"):
        load_dashboard_report(source)


def test_dashboard_requires_nullable_fields_to_be_present() -> None:
    report = _report()
    del report["run"]["model"]  # type: ignore[index]

    with pytest.raises(DashboardDataError, match="missing required fields: model"):
        validate_dashboard_report(report)
