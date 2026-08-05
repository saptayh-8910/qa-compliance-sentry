import json
from datetime import UTC, datetime, timedelta

import pytest

from log_analyzer.analyzer import analyze_events
from log_analyzer.models import LogEvent
from log_analyzer.parser import parse_json_lines


def _event(
    minute: int,
    level: str,
    message: str,
    test_name: str | None = None,
) -> LogEvent:
    return LogEvent(
        timestamp=datetime(2026, 8, 4, 3, minute, tzinfo=UTC),
        level=level,
        message=message,
        test_name=test_name,
    )


def test_parse_json_lines_normalizes_event_fields() -> None:
    lines = [
        "\n",
        json.dumps(
            {
                "timestamp": "2026-08-04T12:00:00+09:00",
                "level": " error ",
                "message": " checkout failed ",
                "test_name": " test_checkout ",
            }
        ),
    ]

    event = parse_json_lines(lines)[0]

    assert event.timestamp == datetime(2026, 8, 4, 3, 0, tzinfo=UTC)
    assert event.level == "ERROR"
    assert event.message == "checkout failed"
    assert event.test_name == "test_checkout"
    assert event.is_failure


def test_parse_json_lines_treats_blank_test_name_as_missing() -> None:
    event = parse_json_lines(
        [
            '{"timestamp":"2026-08-04T03:00:00Z","level":"INFO",'
            '"message":"healthy","test_name":"   "}'
        ]
    )[0]
    assert event.test_name is None


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("not-json", "line 1: invalid JSON"),
        ("[]", "line 1: expected a JSON object"),
        (
            '{"timestamp":"2026-08-04T03:00:00Z","level":"INFO"}',
            "line 1: message must be",
        ),
        (
            '{"timestamp":"2026-08-04T03:00:00","level":"INFO","message":"x"}',
            "line 1: timestamp must include a timezone",
        ),
    ],
)
def test_parse_json_lines_reports_invalid_line_context(line: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_json_lines([line])


def test_analyze_events_ranks_failures_and_merges_incidents() -> None:
    events = [
        _event(0, "INFO", "run started"),
        _event(1, "ERROR", "checkout failed", "test_checkout"),
        _event(2, "ERROR", "API 503", "test_api"),
        _event(4, "FAILED", "checkout failed", "test_cart"),
        _event(20, "CRITICAL", "database invalid", "test_db"),
    ]

    report = analyze_events(events, top_k=2, incident_gap=timedelta(minutes=5))

    assert report.total_events == 5
    assert report.failure_events == 4
    assert [failure.signature for failure in report.top_failures] == [
        "checkout failed",
        "API 503",
    ]
    assert report.top_failures[0].count == 2
    assert report.top_failures[0].tests == ("test_checkout", "test_cart")
    assert len(report.incidents) == 2
    assert report.incidents[0].event_count == 3
    assert report.incidents[1].event_count == 1


def test_analyze_events_handles_no_failures() -> None:
    report = analyze_events([_event(0, "INFO", "healthy")])
    assert report.failure_events == 0
    assert report.top_failures == ()
    assert report.incidents == ()


def test_analyze_events_caps_top_k_to_available_signatures() -> None:
    report = analyze_events([_event(0, "ERROR", "one failure")], top_k=10)
    assert len(report.top_failures) == 1


@pytest.mark.parametrize(
    ("top_k", "gap", "message"),
    [
        (0, timedelta(), "top_k"),
        (1, timedelta(seconds=-1), "incident_gap"),
    ],
)
def test_analyze_events_rejects_invalid_options(
    top_k: int, gap: timedelta, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        analyze_events([], top_k=top_k, incident_gap=gap)
