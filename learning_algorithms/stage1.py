"""Stage 1 array, hashing, and search fundamentals."""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Sequence
from typing import Protocol, Self, TypeVar


class Comparable(Protocol):
    def __lt__(self, other: Self, /) -> bool: ...


Item = TypeVar("Item", bound=Hashable)
OrderedItem = TypeVar("OrderedItem", bound=Comparable)


def two_sum_indices(values: Sequence[int], target: int) -> tuple[int, int] | None:
    """Return indices of two different values whose sum equals ``target``.

    Learning reference: LeetCode 1, Two Sum.
    https://leetcode.com/problems/two-sum/

    A complement lookup map gives O(n) time and O(n) space. Unlike the
    interview problem's guaranteed solution, this project-friendly contract
    returns ``None`` when no pair exists.
    """
    seen: dict[int, int] = {}
    for index, value in enumerate(values):
        complement = target - value
        if complement in seen:
            return seen[complement], index
        seen[value] = index
    return None


def contains_duplicate(values: Iterable[Item]) -> bool:
    """Return whether any value appears more than once.

    Learning reference: LeetCode 217, Contains Duplicate.
    https://leetcode.com/problems/contains-duplicate/

    A set provides O(n) expected time and O(n) space with early exit.
    """
    seen: set[Item] = set()
    for value in values:
        if value in seen:
            return True
        seen.add(value)
    return False


def binary_search(values: Sequence[OrderedItem], target: OrderedItem) -> int:
    """Return the target index in an ascending sequence, or ``-1``.

    Learning reference: LeetCode 704, Binary Search.
    https://leetcode.com/problems/binary-search/

    The caller must provide ascending input. The search runs in O(log n) time
    and O(1) additional space.
    """
    left = 0
    right = len(values) - 1

    while left <= right:
        middle = left + (right - left) // 2
        candidate = values[middle]
        if candidate == target:
            return middle
        if candidate < target:
            left = middle + 1
        else:
            right = middle - 1

    return -1
