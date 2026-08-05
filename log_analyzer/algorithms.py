"""Interview algorithms adapted to practical QA log analysis."""

from __future__ import annotations

from collections.abc import Hashable, Sequence
from datetime import datetime
from typing import TypeVar

Item = TypeVar("Item", bound=Hashable)
Boundary = TypeVar("Boundary", int, datetime)


def top_k_frequent(items: Sequence[Item], k: int) -> list[Item]:
    """Return the k most frequent items, preserving first-seen order for ties.

    Learning reference: LeetCode 347, Top K Frequent Elements.
    https://leetcode.com/problems/top-k-frequent-elements/

    A frequency map plus buckets gives O(n) time and O(n) space.
    """
    if k < 1:
        raise ValueError("k must be at least 1")

    frequencies: dict[Item, int] = {}
    for item in items:
        frequencies[item] = frequencies.get(item, 0) + 1

    if k > len(frequencies):
        raise ValueError("k cannot exceed the number of unique items")

    buckets: list[list[Item]] = [[] for _ in range(len(items) + 1)]
    for item, count in frequencies.items():
        buckets[count].append(item)

    result: list[Item] = []
    for count in range(len(buckets) - 1, 0, -1):
        for item in buckets[count]:
            result.append(item)
            if len(result) == k:
                return result

    return result


def merge_intervals(
    intervals: Sequence[tuple[Boundary, Boundary]],
) -> list[tuple[Boundary, Boundary]]:
    """Merge overlapping intervals after validating their boundaries.

    Learning reference: LeetCode 56, Merge Intervals.
    https://leetcode.com/problems/merge-intervals/

    Sorting dominates the algorithm: O(n log n) time and O(n) output space.
    """
    if not intervals:
        return []

    for start, end in intervals:
        if start > end:
            raise ValueError("interval start cannot be after its end")

    ordered = sorted(intervals, key=lambda interval: interval[0])
    merged = [ordered[0]]

    for start, end in ordered[1:]:
        current_start, current_end = merged[-1]
        if start <= current_end:
            merged[-1] = (current_start, max(current_end, end))
        else:
            merged.append((start, end))

    return merged
