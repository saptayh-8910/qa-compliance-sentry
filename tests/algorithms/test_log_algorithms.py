from datetime import UTC, datetime, timedelta

import pytest

from log_analyzer.algorithms import merge_intervals, top_k_frequent


def test_top_k_frequent_matches_interview_example() -> None:
    assert top_k_frequent([1, 1, 1, 2, 2, 3], 2) == [1, 2]


def test_top_k_frequent_handles_one_item() -> None:
    assert top_k_frequent(["timeout"], 1) == ["timeout"]


def test_top_k_frequent_uses_first_seen_order_for_ties() -> None:
    failures = ["API 503", "timeout", "timeout", "API 503", "bad total"]
    assert top_k_frequent(failures, 2) == ["API 503", "timeout"]


@pytest.mark.parametrize("k", [0, -1])
def test_top_k_frequent_rejects_non_positive_k(k: int) -> None:
    with pytest.raises(ValueError, match="at least 1"):
        top_k_frequent([1], k)


def test_top_k_frequent_rejects_k_above_unique_count() -> None:
    with pytest.raises(ValueError, match="unique"):
        top_k_frequent([1, 1], 2)


def test_merge_intervals_matches_interview_example() -> None:
    intervals = [(1, 3), (2, 6), (8, 10), (15, 18)]
    assert merge_intervals(intervals) == [(1, 6), (8, 10), (15, 18)]


def test_merge_intervals_combines_touching_boundaries() -> None:
    assert merge_intervals([(1, 4), (4, 5)]) == [(1, 5)]


def test_merge_intervals_supports_incident_timestamps() -> None:
    start = datetime(2026, 8, 4, 3, 0, tzinfo=UTC)
    intervals = [
        (start, start + timedelta(minutes=5)),
        (start + timedelta(minutes=3), start + timedelta(minutes=8)),
        (start + timedelta(minutes=20), start + timedelta(minutes=25)),
    ]
    assert merge_intervals(intervals) == [
        (start, start + timedelta(minutes=8)),
        (start + timedelta(minutes=20), start + timedelta(minutes=25)),
    ]


def test_merge_intervals_handles_empty_input() -> None:
    assert merge_intervals([]) == []


def test_merge_intervals_rejects_reversed_boundaries() -> None:
    with pytest.raises(ValueError, match="start"):
        merge_intervals([(5, 1)])
