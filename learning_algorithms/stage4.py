"""Stage 4 dynamic-programming, heap, and sliding-window foundations."""

from __future__ import annotations

import heapq
from collections.abc import Iterable, Sequence
from math import isfinite

Number = int | float


def edit_distance(first: str, second: str) -> int:
    """Return the minimum single-character edits needed to transform text.

    Learning reference: LeetCode 72, Edit Distance.
    https://leetcode.com/problems/edit-distance/

    Dynamic programming compares insertion, deletion, and replacement costs.
    The implementation keeps only the previous row, giving O(mn) time and
    O(min(m, n)) additional space.
    """
    if len(first) < len(second):
        first, second = second, first

    previous = list(range(len(second) + 1))
    for first_index, first_character in enumerate(first, start=1):
        current = [first_index]
        for second_index, second_character in enumerate(second, start=1):
            insertion = current[-1] + 1
            deletion = previous[second_index] + 1
            replacement = previous[second_index - 1] + (
                first_character != second_character
            )
            current.append(min(insertion, deletion, replacement))
        previous = current
    return previous[-1]


def _number(value: Number, *, label: str) -> Number:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must contain only numbers")
    if not isfinite(float(value)):
        raise ValueError(f"{label} must contain only finite numbers")
    return value


class KthLargest:
    """Track the kth-largest value in a stream using a size-k min-heap.

    Learning reference: LeetCode 703, Kth Largest Element in a Stream.
    https://leetcode.com/problems/kth-largest-element-in-a-stream/

    The heap stores only the largest ``k`` values seen. Its root is therefore
    the kth-largest value. Construction costs O(n log k), each addition costs
    O(log k), and storage is O(k).
    """

    def __init__(self, k: int, values: Iterable[Number] = ()) -> None:
        if isinstance(k, bool) or not isinstance(k, int) or k < 1:
            raise ValueError("kth-largest rank must be an integer of at least 1")
        initial_values = tuple(values)
        if len(initial_values) < k - 1:
            raise ValueError("kth-largest stream needs at least k - 1 initial values")
        self.k = k
        self._heap: list[Number] = []
        for value in initial_values:
            self._include(_number(value, label="kth-largest stream"))

    def __len__(self) -> int:
        return len(self._heap)

    def _include(self, value: Number) -> None:
        if len(self._heap) < self.k:
            heapq.heappush(self._heap, value)
        elif value > self._heap[0]:
            heapq.heapreplace(self._heap, value)

    @property
    def kth_largest(self) -> Number:
        """Return the current threshold once at least k values were observed."""
        if len(self._heap) < self.k:
            raise RuntimeError("kth-largest value is unavailable until the next add")
        return self._heap[0]

    def add(self, value: Number) -> Number:
        """Add one value and return the current kth-largest threshold."""
        self._include(_number(value, label="kth-largest stream"))
        return self.kth_largest


def maximum_average_subarray(values: Sequence[Number], window_size: int) -> float:
    """Return the largest average among fixed-size contiguous windows.

    Learning reference: LeetCode 643, Maximum Average Subarray I.
    https://leetcode.com/problems/maximum-average-subarray-i/

    A rolling sum removes the value leaving the window and adds the value
    entering it. This gives O(n) time and O(1) additional working space.
    """
    if not values:
        raise ValueError("rolling average requires at least one value")
    if (
        isinstance(window_size, bool)
        or not isinstance(window_size, int)
        or window_size < 1
        or window_size > len(values)
    ):
        raise ValueError("window size must be between 1 and the number of values")

    validated = tuple(_number(value, label="rolling average") for value in values)
    rolling_sum = sum(validated[:window_size])
    maximum_sum = rolling_sum
    for index in range(window_size, len(validated)):
        rolling_sum += validated[index] - validated[index - window_size]
        maximum_sum = max(maximum_sum, rolling_sum)
    return maximum_sum / window_size
