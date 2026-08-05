"""Read named CI pipeline dependencies from JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_pipeline(path: Path) -> tuple[list[str], list[tuple[str, str]]]:
    if not path.is_file():
        raise FileNotFoundError(f"pipeline file does not exist: {path}")

    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("pipeline file contains invalid JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("pipeline definition must be a JSON object")

    jobs = payload.get("jobs")
    raw_dependencies = payload.get("dependencies", [])
    if not isinstance(jobs, list) or not all(isinstance(job, str) for job in jobs):
        raise ValueError("jobs must be a JSON array of strings")
    if not isinstance(raw_dependencies, list):
        raise ValueError("dependencies must be a JSON array")

    dependencies: list[tuple[str, str]] = []
    for index, dependency in enumerate(raw_dependencies):
        if (
            not isinstance(dependency, list)
            or len(dependency) != 2
            or not all(isinstance(value, str) for value in dependency)
        ):
            raise ValueError(f"dependency {index} must contain [job, prerequisite]")
        dependencies.append((dependency[0], dependency[1]))

    return jobs, dependencies
