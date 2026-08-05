import pytest

from pipeline_validator.dependencies import can_finish_all


def test_can_finish_all_matches_acyclic_interview_example() -> None:
    assert can_finish_all(2, [(1, 0)])


def test_can_finish_all_matches_cyclic_interview_example() -> None:
    assert not can_finish_all(2, [(1, 0), (0, 1)])


def test_can_finish_all_handles_disconnected_jobs() -> None:
    assert can_finish_all(5, [(1, 0), (3, 2)])


def test_can_finish_all_detects_self_dependency() -> None:
    assert not can_finish_all(1, [(0, 0)])


def test_can_finish_all_accepts_empty_pipeline() -> None:
    assert can_finish_all(0, [])


def test_can_finish_all_rejects_negative_job_count() -> None:
    with pytest.raises(ValueError, match="negative"):
        can_finish_all(-1, [])


@pytest.mark.parametrize("dependency", [[(2, 0)], [(1, -1)]])
def test_can_finish_all_rejects_unknown_indexes(
    dependency: list[tuple[int, int]],
) -> None:
    with pytest.raises(ValueError, match="unknown"):
        can_finish_all(2, dependency)
