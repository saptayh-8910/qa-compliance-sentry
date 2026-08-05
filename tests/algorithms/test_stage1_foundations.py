from collections.abc import Iterator

import pytest

from learning_algorithms.stage1 import (
    binary_search,
    contains_duplicate,
    two_sum_indices,
)


@pytest.mark.parametrize(
    ("values", "target", "expected"),
    [
        ([2, 7, 11, 15], 9, (0, 1)),
        ([3, 2, 4], 6, (1, 2)),
        ([3, 3], 6, (0, 1)),
    ],
)
def test_two_sum_matches_interview_examples(
    values: list[int], target: int, expected: tuple[int, int]
) -> None:
    assert two_sum_indices(values, target) == expected


def test_two_sum_returns_none_without_a_pair() -> None:
    assert two_sum_indices([1, 2, 3], 20) is None


def test_two_sum_does_not_reuse_one_value() -> None:
    assert two_sum_indices([4], 8) is None


def test_two_sum_finds_response_times_matching_budget() -> None:
    response_times_ms = [120, 350, 180, 500]
    assert two_sum_indices(response_times_ms, 300) == (0, 2)


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([1, 2, 3, 1], True),
        ([1, 2, 3, 4], False),
        ([], False),
    ],
)
def test_contains_duplicate_matches_interview_examples(
    values: list[int], expected: bool
) -> None:
    assert contains_duplicate(values) is expected


def test_contains_duplicate_detects_repeated_test_case_id() -> None:
    case_ids = ["TC-LOGIN-001", "TC-CART-001", "TC-LOGIN-001"]
    assert contains_duplicate(case_ids)


def test_contains_duplicate_accepts_a_stream() -> None:
    def case_id_stream() -> Iterator[str]:
        yield "TC-001"
        yield "TC-002"
        yield "TC-002"

    assert contains_duplicate(case_id_stream())


@pytest.mark.parametrize(
    ("values", "target", "expected"),
    [
        ([-1, 0, 3, 5, 9, 12], 9, 4),
        ([-1, 0, 3, 5, 9, 12], 2, -1),
        ([], 5, -1),
        ([5], 5, 0),
    ],
)
def test_binary_search_matches_interview_examples(
    values: list[int], target: int, expected: int
) -> None:
    assert binary_search(values, target) == expected


def test_binary_search_finds_sorted_test_case_id() -> None:
    case_ids = ["TC-API-001", "TC-API-002", "TC-DB-001", "TC-E2E-001"]
    assert binary_search(case_ids, "TC-DB-001") == 2
