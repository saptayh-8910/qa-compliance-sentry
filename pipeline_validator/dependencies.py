"""Graph algorithms for validating CI job dependencies."""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence


def can_finish_all(
    job_count: int,
    dependencies: Sequence[tuple[int, int]],
) -> bool:
    """Return whether every numbered job can run without a dependency cycle.

    Each pair is ``(job, prerequisite)``.

    Learning reference: LeetCode 207, Course Schedule.
    https://leetcode.com/problems/course-schedule/

    Kahn's topological-sort algorithm runs in O(V + E) time and space.
    """
    if job_count < 0:
        raise ValueError("job_count cannot be negative")

    graph: list[list[int]] = [[] for _ in range(job_count)]
    indegree = [0] * job_count

    for job, prerequisite in dependencies:
        if not 0 <= job < job_count or not 0 <= prerequisite < job_count:
            raise ValueError("dependency contains an unknown job index")
        graph[prerequisite].append(job)
        indegree[job] += 1

    ready = deque(index for index, count in enumerate(indegree) if count == 0)
    completed = 0

    while ready:
        prerequisite = ready.popleft()
        completed += 1
        for dependent in graph[prerequisite]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)

    return completed == job_count


def validate_pipeline(
    jobs: Sequence[str],
    dependencies: Sequence[tuple[str, str]],
) -> bool:
    """Validate named pipeline jobs using the Course Schedule algorithm."""
    normalized_jobs = [job.strip() for job in jobs]
    if any(not job for job in normalized_jobs):
        raise ValueError("job names must be non-empty")
    if len(set(normalized_jobs)) != len(normalized_jobs):
        raise ValueError("job names must be unique")

    job_indexes = {job: index for index, job in enumerate(normalized_jobs)}
    indexed_dependencies: list[tuple[int, int]] = []
    for job, prerequisite in dependencies:
        normalized_job = job.strip()
        normalized_prerequisite = prerequisite.strip()
        if normalized_job not in job_indexes:
            raise ValueError(f"unknown job in dependency: {job}")
        if normalized_prerequisite not in job_indexes:
            raise ValueError(f"unknown prerequisite: {prerequisite}")
        indexed_dependencies.append(
            (job_indexes[normalized_job], job_indexes[normalized_prerequisite])
        )

    return can_finish_all(len(normalized_jobs), indexed_dependencies)
