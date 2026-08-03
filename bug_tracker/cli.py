from __future__ import annotations

from pathlib import Path

import typer

from bug_tracker.models import Bug, BugSeverity, BugStatus
from bug_tracker.storage import BugStorage

app = typer.Typer(
    name="bug-tracker",
    help="Bug Tracker CLI — add, update, search, and list bugs (JSON storage).",
)
DEFAULT_DB = Path("data/bugs.json")


def _storage(path: Path | None) -> BugStorage:
    return BugStorage(path or DEFAULT_DB)


@app.command("add")
def add_bug(
    title: str = typer.Argument(..., help="Short bug title"),
    description: str = typer.Option("", "--description", "-d"),
    severity: BugSeverity = typer.Option(BugSeverity.MEDIUM, "--severity", "-s"),
    db: Path | None = typer.Option(None, "--db", help="JSON file path"),
) -> None:
    """Add a new bug."""
    bug = Bug(title=title, description=description, severity=severity)
    _storage(db).add(bug)
    typer.echo(f"Created bug {bug.id}: {bug.title} [{bug.status.value}]")


@app.command("update")
def update_bug(
    bug_id: str = typer.Argument(..., help="Bug UUID"),
    status: BugStatus = typer.Option(..., "--status"),
    db: Path | None = typer.Option(None, "--db"),
) -> None:
    """Update bug status."""
    try:
        bug = _storage(db).update_status(bug_id, status)
    except KeyError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Updated {bug.id} -> {bug.status.value}")


@app.command("search")
def search_bugs(
    query: str = typer.Argument(
        ..., help="Search title, description, status, severity"
    ),
    db: Path | None = typer.Option(None, "--db"),
) -> None:
    """Search bugs by keyword."""
    results = _storage(db).search(query)
    if not results:
        typer.echo("No bugs found.")
        raise typer.Exit(code=0)
    for bug in results:
        typer.echo(
            f"{bug.id} | {bug.status.value:12} | {bug.severity.value:8} | {bug.title}"
        )


@app.command("list")
def list_bugs(
    db: Path | None = typer.Option(None, "--db"),
) -> None:
    """List all bugs."""
    bugs = _storage(db).load_all()
    if not bugs:
        typer.echo("No bugs recorded.")
        raise typer.Exit(code=0)
    for bug in bugs:
        typer.echo(
            f"{bug.id} | {bug.status.value:12} | {bug.severity.value:8} | {bug.title}"
        )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
