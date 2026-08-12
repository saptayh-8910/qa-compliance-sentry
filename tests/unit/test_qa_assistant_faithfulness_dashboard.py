from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from qa_assistant.faithfulness import (
    DeterministicFaithfulnessJudge,
    validate_faithfulness_judge,
)
from qa_assistant.faithfulness_dashboard import (
    FaithfulnessDashboardDataError,
    load_faithfulness_report,
    render_faithfulness_dashboard,
    validate_faithfulness_report,
    write_faithfulness_dashboard,
)
from qa_assistant.faithfulness_reporting import faithfulness_report_data


def _report() -> dict[str, object]:
    return faithfulness_report_data(
        validate_faithfulness_judge(DeterministicFaithfulnessJudge()),
        run_id="faithfulness-test",
        created_at=datetime(2026, 8, 12, 12, tzinfo=UTC),
    )


def test_dashboard_explains_metrics_thresholds_and_scope() -> None:
    rendered = render_faithfulness_dashboard(_report())

    assert "Can this judge detect unsupported claims?" in rendered
    assert "Exact label accuracy" in rendered
    assert "Unfaithful precision" in rendered
    assert "Unfaithful recall" in rendered
    assert "Unfaithful F1" in rendered
    assert "False negatives" in rendered
    assert "Evaluation criteria" in rendered
    assert "Accuracy ≥ 90%" in rendered
    assert "Unfaithful recall ≥ 95%" in rendered
    assert "False negatives ≤ 0" in rendered
    assert "does not prove universal semantic understanding" in rendered
    assert "Why the human labelled it this way" in rendered
    assert 'data-human-label="contradicted"' in rendered
    assert "card.hidden=!show" in rendered


def test_dashboard_escapes_all_untrusted_claim_strings() -> None:
    report = _report()
    payload = '<script>alert("unsafe")</script>'
    claim = report["claims"][0]  # type: ignore[index]
    claim["claim_id"] = payload
    claim["evidence"] = payload
    claim["claim"] = payload
    claim["human_explanation"] = payload
    report["run"]["judge"] = payload  # type: ignore[index]

    rendered = render_faithfulness_dashboard(report)

    assert payload not in rendered
    assert rendered.count("&lt;script&gt;") == 5


def test_dashboard_loads_and_writes_standalone_html(tmp_path: Path) -> None:
    source = tmp_path / "faithfulness.json"
    output = tmp_path / "nested" / "faithfulness.html"
    source.write_text(json.dumps(_report()), encoding="utf-8")

    loaded = load_faithfulness_report(source)
    write_faithfulness_dashboard(source, output)

    assert loaded["schema_version"] == "1.0"
    assert output.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert tuple(output.parent.glob("*.tmp")) == ()


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        ("schema_version", "2.0", "unsupported faithfulness report"),
        ("summary.example_count", 14, "summary counts conflict"),
        ("summary.accuracy", 0.9, "does not match counts"),
        (
            "summary.unfaithful_precision",
            0.9,
            "unfaithful_precision does not match claim labels",
        ),
        (
            "summary.unfaithful_recall",
            0.99,
            "unfaithful_recall does not match claim labels",
        ),
        (
            "summary.unfaithful_f1",
            0.9,
            "unfaithful_f1 does not match claim labels",
        ),
        ("summary.validated", False, "does not match validation policy"),
        (
            "summary.confusion_matrix.supported.supported",
            4,
            "confusion_matrix does not match",
        ),
        ("claims.0.correct", False, "does not match its labels"),
        ("claims.0.human_label", "unknown", "labels must be"),
    ],
)
def test_dashboard_rejects_inconsistent_or_invalid_evidence(
    path: str, value: object, message: str
) -> None:
    report = deepcopy(_report())
    target: object = report
    parts = path.split(".")
    for part in parts[:-1]:
        target = target[int(part)] if part.isdigit() else target[part]  # type: ignore[index]
    target[parts[-1]] = value  # type: ignore[index]

    with pytest.raises(FaithfulnessDashboardDataError, match=message):
        validate_faithfulness_report(report)


def test_dashboard_rejects_matrix_that_only_matches_summary_totals() -> None:
    report = _report()
    matrix = report["summary"]["confusion_matrix"]  # type: ignore[index]
    matrix["supported"]["supported"] = 4
    matrix["contradicted"]["contradicted"] = 6

    with pytest.raises(
        FaithfulnessDashboardDataError,
        match="confusion_matrix does not match claim labels",
    ):
        validate_faithfulness_report(report)


def test_dashboard_reports_invalid_json_location(tmp_path: Path) -> None:
    source = tmp_path / "invalid.json"
    source.write_text('{"schema_version":', encoding="utf-8")

    with pytest.raises(FaithfulnessDashboardDataError, match=r"line 1, column 19"):
        load_faithfulness_report(source)
