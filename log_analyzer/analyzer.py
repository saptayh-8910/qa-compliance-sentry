"""Convert structured QA events into failure and incident summaries."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import timedelta

from log_analyzer.algorithms import merge_intervals, top_k_frequent
from log_analyzer.models import (
    AnalysisReport,
    FailureSummary,
    IncidentWindow,
    LogEvent,
)


def analyze_events(
    events: Sequence[LogEvent],
    *,
    top_k: int = 5,
    incident_gap: timedelta = timedelta(minutes=5),
) -> AnalysisReport:
    """Rank recurring failures and merge nearby failures into incidents."""
    if top_k < 1:
        raise ValueError("top_k must be at least 1")
    if incident_gap < timedelta(0):
        raise ValueError("incident_gap cannot be negative")

    failures = sorted(
        (event for event in events if event.is_failure),
        key=lambda event: event.timestamp,
    )
    if not failures:
        return AnalysisReport(len(events), 0, (), ())

    signatures = [event.message for event in failures]
    unique_count = len(set(signatures))
    ranked_signatures = top_k_frequent(signatures, min(top_k, unique_count))

    grouped: dict[str, list[LogEvent]] = defaultdict(list)
    for event in failures:
        grouped[event.message].append(event)

    top_failures = tuple(
        FailureSummary(
            signature=signature,
            count=len(grouped[signature]),
            first_seen=grouped[signature][0].timestamp,
            last_seen=grouped[signature][-1].timestamp,
            tests=tuple(
                dict.fromkeys(
                    event.test_name
                    for event in grouped[signature]
                    if event.test_name is not None
                )
            ),
        )
        for signature in ranked_signatures
    )

    merged = merge_intervals(
        [(event.timestamp, event.timestamp + incident_gap) for event in failures]
    )
    incidents = tuple(
        IncidentWindow(
            start=start,
            end=end,
            event_count=sum(start <= event.timestamp <= end for event in failures),
        )
        for start, end in merged
    )

    return AnalysisReport(
        total_events=len(events),
        failure_events=len(failures),
        top_failures=top_failures,
        incidents=incidents,
    )
