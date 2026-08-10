from __future__ import annotations

import pytest

from learning_algorithms.stage4 import (
    KthLargest,
    edit_distance,
    maximum_average_subarray,
)


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        ("horse", "ros", 3),
        ("intention", "execution", 5),
        ("", "", 0),
        ("", "answer", 6),
        ("citation", "citation", 0),
        ("cat", "cut", 1),
    ],
)
def test_edit_distance_matches_interview_examples(
    first: str, second: str, expected: int
) -> None:
    assert edit_distance(first, second) == expected
    assert edit_distance(second, first) == expected


def test_edit_distance_measures_literal_answer_regression() -> None:
    baseline = "Coverage runs before merge [1]."
    candidate = "Coverage runs after merge [1]."

    assert edit_distance(baseline, candidate) == 5


def test_kth_largest_matches_interview_sequence() -> None:
    tracker = KthLargest(3, [4, 5, 8, 2])

    assert tracker.kth_largest == 4
    assert tracker.add(3) == 4
    assert tracker.add(5) == 5
    assert tracker.add(10) == 5
    assert tracker.add(9) == 8
    assert tracker.add(4) == 8
    assert len(tracker) == 3


def test_kth_largest_supports_duplicate_quality_scores() -> None:
    tracker = KthLargest(2, [0.9])

    assert tracker.add(0.9) == pytest.approx(0.9)
    assert tracker.add(0.8) == pytest.approx(0.9)
    assert tracker.add(1.0) == pytest.approx(0.9)


def test_kth_largest_tracks_top_stream_value_when_k_is_one() -> None:
    tracker = KthLargest(1)

    assert tracker.add(-2) == -2
    assert tracker.add(-3) == -2
    assert tracker.add(4) == 4


def test_kth_largest_waits_for_the_kth_observation() -> None:
    tracker = KthLargest(3, [0.5, 0.7])

    with pytest.raises(RuntimeError, match="unavailable"):
        _ = tracker.kth_largest
    assert tracker.add(0.6) == pytest.approx(0.5)


@pytest.mark.parametrize("rank", [0, -1, True, 1.5])
def test_kth_largest_rejects_invalid_rank(rank: object) -> None:
    with pytest.raises(ValueError, match="integer of at least 1"):
        KthLargest(rank)  # type: ignore[arg-type]


def test_kth_largest_rejects_insufficient_initial_history() -> None:
    with pytest.raises(ValueError, match="at least k - 1"):
        KthLargest(3, [0.5])


@pytest.mark.parametrize("value", [True, float("nan"), float("inf")])
def test_kth_largest_rejects_invalid_stream_values(value: object) -> None:
    tracker = KthLargest(1)

    with pytest.raises(ValueError, match="numbers"):
        tracker.add(value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("values", "window_size", "expected"),
    [
        ([1, 12, -5, -6, 50, 3], 4, 12.75),
        ([5], 1, 5.0),
        ([-5, -1, -3], 2, -2.0),
        ([0.5, 0.8, 0.9], 2, 0.85),
    ],
)
def test_maximum_average_subarray_matches_interview_examples(
    values: list[float], window_size: int, expected: float
) -> None:
    assert maximum_average_subarray(values, window_size) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("values", "window_size", "message"),
    [
        ([], 1, "at least one value"),
        ([1, 2], 0, "between 1"),
        ([1, 2], 3, "between 1"),
        ([1, 2], True, "between 1"),
        ([1, float("nan")], 1, "finite numbers"),
        ([1, True], 1, "only numbers"),
    ],
)
def test_maximum_average_subarray_rejects_invalid_input(
    values: list[object], window_size: object, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        maximum_average_subarray(  # type: ignore[arg-type]
            values,
            window_size,
        )
