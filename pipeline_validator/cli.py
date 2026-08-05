"""Command-line interface for CI dependency validation."""

from __future__ import annotations

from pathlib import Path

import typer

from pipeline_validator.dependencies import validate_pipeline
from pipeline_validator.parser import load_pipeline

app = typer.Typer(
    name="pipeline-validator",
    help="Detect dependency cycles in a named CI pipeline.",
)


@app.callback()
def root() -> None:
    """Validate whether every CI job can run."""


@app.command("validate")
def validate(
    pipeline_file: Path = typer.Argument(..., help="Pipeline JSON definition"),
) -> None:
    """Validate one pipeline definition."""
    try:
        jobs, dependencies = load_pipeline(pipeline_file)
        is_valid = validate_pipeline(jobs, dependencies)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    if not is_valid:
        typer.echo("Pipeline contains a dependency cycle.", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Pipeline is valid: {len(jobs)} jobs, {len(dependencies)} dependencies")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
