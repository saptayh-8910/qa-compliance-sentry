import json
from pathlib import Path

from typer.testing import CliRunner

from pipeline_validator.cli import app

runner = CliRunner()


def _write_pipeline(path: Path, dependencies: list[list[str]]) -> None:
    path.write_text(
        json.dumps(
            {
                "jobs": ["quality", "tests"],
                "dependencies": dependencies,
            }
        ),
        encoding="utf-8",
    )


def test_cli_accepts_valid_pipeline(tmp_path: Path) -> None:
    path = tmp_path / "pipeline.json"
    _write_pipeline(path, [["tests", "quality"]])

    result = runner.invoke(app, ["validate", str(path)])

    assert result.exit_code == 0
    assert "Pipeline is valid: 2 jobs, 1 dependencies" in result.stdout


def test_cli_rejects_dependency_cycle(tmp_path: Path) -> None:
    path = tmp_path / "pipeline.json"
    _write_pipeline(path, [["tests", "quality"], ["quality", "tests"]])

    result = runner.invoke(app, ["validate", str(path)])

    assert result.exit_code == 1
    assert "dependency cycle" in result.output


def test_cli_rejects_missing_pipeline(tmp_path: Path) -> None:
    result = runner.invoke(app, ["validate", str(tmp_path / "missing.json")])
    assert result.exit_code == 1
    assert "does not exist" in result.output
