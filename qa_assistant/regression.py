"""QA-oriented adapters for answer regression and evaluation score trends."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from learning_algorithms.stage4 import (
    KthLargest,
    edit_distance,
    maximum_average_subarray,
)


@dataclass(frozen=True, slots=True)
class AnswerComparison:
    """Surface-level difference between a reference and candidate answer."""

    edit_count: int
    similarity_ratio: float
    reference_length: int
    candidate_length: int

    @property
    def changed(self) -> bool:
        return self.edit_count > 0


def compare_answer_text(reference: str, candidate: str) -> AnswerComparison:
    """Measure literal answer change without claiming semantic equivalence."""
    changes = edit_distance(reference, candidate)
    longest_length = max(len(reference), len(candidate))
    similarity = 1.0 if longest_length == 0 else 1 - changes / longest_length
    return AnswerComparison(
        edit_count=changes,
        similarity_ratio=similarity,
        reference_length=len(reference),
        candidate_length=len(candidate),
    )


@dataclass(frozen=True, slots=True)
class EvaluationScoreTrend:
    """Two explainable thresholds calculated from bounded quality scores."""

    sample_count: int
    kth_rank: int
    kth_highest_score: float
    window_size: int
    maximum_window_average: float


def analyze_evaluation_scores(
    scores: tuple[float, ...],
    *,
    kth_rank: int,
    window_size: int,
) -> EvaluationScoreTrend:
    """Summarize top-score threshold and best contiguous evaluation window."""
    if not scores:
        raise ValueError("evaluation score history cannot be empty")
    if any(
        isinstance(score, bool)
        or not isinstance(score, (int, float))
        or not isfinite(float(score))
        or not 0 <= score <= 1
        for score in scores
    ):
        raise ValueError("evaluation scores must be finite numbers between 0 and 1")
    if (
        isinstance(kth_rank, bool)
        or not isinstance(kth_rank, int)
        or not 1 <= kth_rank <= len(scores)
    ):
        raise ValueError("evaluation kth rank must fit the score history")

    threshold = KthLargest(kth_rank, scores)
    rolling_average = maximum_average_subarray(scores, window_size)
    return EvaluationScoreTrend(
        sample_count=len(scores),
        kth_rank=kth_rank,
        kth_highest_score=float(threshold.kth_largest),
        window_size=window_size,
        maximum_window_average=rolling_average,
    )
