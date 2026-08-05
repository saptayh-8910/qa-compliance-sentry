"""Command-line interface for structured QA log analysis."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import typer

from log_analyzer.analyzer import analyze_events
from log_analyzer.parser import load_json_lines

app = typer.Typer(
    name="log-analyzer",
    help="Rank recurring QA failures and consolidate incident windows.",
)


@app.callback()
def root() -> None:
    """Analyze structured test logs for recurring failures and incidents."""


@app.command("analyze")
def analyze(
    log_file: Path = typer.Argument(..., help="Newline-delimited JSON log file"),
    top: int = typer.Option(5, "--top", "-k", min=1),
    incident_gap_seconds: int = typer.Option(
        300,
        "--incident-gap-seconds",
        min=0,
        help="Merge failures occurring within this many seconds",
    ),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Analyze one JSONL file and optionally save a JSON report."""
    try:
        events = load_json_lines(log_file)
        report = analyze_events(
            events,
            top_k=top,
            incident_gap=timedelta(seconds=incident_gap_seconds),
        )
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"Analyzed {report.total_events} events: "
        f"{report.failure_events} failures, {len(report.incidents)} incidents"
    )
    for rank, failure in enumerate(report.top_failures, start=1):
        typer.echo(f"{rank}. {failure.signature} ({failure.count})")

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report.to_dict(), indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        typer.echo(f"Report written to {output}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
