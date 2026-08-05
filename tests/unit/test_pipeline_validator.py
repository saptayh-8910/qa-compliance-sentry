import json
from pathlib import Path

import pytest

from pipeline_validator.dependencies import validate_pipeline
from pipeline_validator.parser import load_pipeline


def test_validate_pipeline_accepts_named_dependency_chain() -> None:
    jobs = ["quality", "unit-tests", "container-smoke"]
    dependencies = [
        ("unit-tests", "quality"),
        ("container-smoke", "unit-tests"),
    ]
    assert validate_pipeline(jobs, dependencies)


def test_validate_pipeline_detects_named_cycle() -> None:
    jobs = ["quality", "unit-tests"]
    dependencies = [("unit-tests", "quality"), ("quality", "unit-tests")]
    assert not validate_pipeline(jobs, dependencies)


@pytest.mark.parametrize(
    ("jobs", "dependencies", "message"),
    [
        (["quality", " quality "], [], "unique"),
        (["quality", ""], [], "non-empty"),
        (["quality"], [("missing", "quality")], "unknown job"),
        (["quality"], [("quality", "missing")], "unknown prerequisite"),
    ],
)
def test_validate_pipeline_rejects_invalid_names(
    jobs: list[str],
    dependencies: list[tuple[str, str]],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_pipeline(jobs, dependencies)


def test_load_pipeline_reads_json_definition(tmp_path: Path) -> None:
    path = tmp_path / "pipeline.json"
    path.write_text(
        json.dumps(
            {
                "jobs": ["quality", "unit-tests"],
                "dependencies": [["unit-tests", "quality"]],
            }
        ),
        encoding="utf-8",
    )
    assert load_pipeline(path) == (
        ["quality", "unit-tests"],
        [("unit-tests", "quality")],
    )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ("not-json", "invalid JSON"),
        ("[]", "JSON object"),
        ('{"jobs":"quality"}', "array of strings"),
        ('{"jobs":[],"dependencies":"quality"}', "JSON array"),
        ('{"jobs":[],"dependencies":[["quality"]]}', "must contain"),
    ],
)
def test_load_pipeline_rejects_malformed_definitions(
    tmp_path: Path, payload: str, message: str
) -> None:
    path = tmp_path / "pipeline.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_pipeline(path)


def test_load_pipeline_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        load_pipeline(tmp_path / "missing.json")
