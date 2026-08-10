from __future__ import annotations

import pytest

from qa_assistant.regression import analyze_evaluation_scores, compare_answer_text


def test_answer_comparison_reports_unchanged_and_empty_answers() -> None:
    unchanged = compare_answer_text("Grounded answer [1].", "Grounded answer [1].")
    empty = compare_answer_text("", "")

    assert not unchanged.changed
    assert unchanged.edit_count == 0
    assert unchanged.similarity_ratio == 1.0
    assert unchanged.reference_length == unchanged.candidate_length == 20
    assert not empty.changed
    assert empty.similarity_ratio == 1.0


def test_answer_comparison_quantifies_literal_change_without_semantic_claim() -> None:
    comparison = compare_answer_text("cat", "cut")

    assert comparison.changed
    assert comparison.edit_count == 1
    assert comparison.similarity_ratio == pytest.approx(2 / 3)
    assert comparison.reference_length == comparison.candidate_length == 3


def test_evaluation_score_analysis_returns_threshold_and_best_window() -> None:
    trend = analyze_evaluation_scores(
        (0.5, 0.8, 0.9, 0.6, 1.0),
        kth_rank=2,
        window_size=3,
    )

    assert trend.sample_count == 5
    assert trend.kth_rank == 2
    assert trend.kth_highest_score == pytest.approx(0.9)
    assert trend.window_size == 3
    assert trend.maximum_window_average == pytest.approx(5 / 6)


@pytest.mark.parametrize(
    ("scores", "kth_rank", "window_size", "message"),
    [
        ((), 1, 1, "cannot be empty"),
        ((0.5, 1.1), 1, 1, "between 0 and 1"),
        ((0.5, float("nan")), 1, 1, "between 0 and 1"),
        ((0.5, True), 1, 1, "between 0 and 1"),
        ((0.5,), 0, 1, "rank must fit"),
        ((0.5,), 2, 1, "rank must fit"),
        ((0.5,), True, 1, "rank must fit"),
        ((0.5,), 1, 2, "window size"),
    ],
)
def test_evaluation_score_analysis_rejects_invalid_history(
    scores: tuple[object, ...],
    kth_rank: object,
    window_size: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        analyze_evaluation_scores(  # type: ignore[arg-type]
            scores,
            kth_rank=kth_rank,
            window_size=window_size,
        )
