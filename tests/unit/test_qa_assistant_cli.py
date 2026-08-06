from pathlib import Path

from typer.testing import CliRunner

from qa_assistant.cli import app

runner = CliRunner()


def test_cli_retrieves_cited_context_from_repeated_sources(tmp_path: Path) -> None:
    first = tmp_path / "ci.md"
    second = tmp_path / "browser.txt"
    first.write_text(
        "# Quality gates\n\nCoverage blocks unsafe pull requests.", encoding="utf-8"
    )
    second.write_text("Playwright runs Chromium smoke tests.", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "retrieve",
            "coverage pull requests",
            "--source",
            str(first),
            "--source",
            str(second),
            "--top",
            "1",
        ],
    )

    assert result.exit_code == 0
    assert "Indexed 2 documents into 2 chunks." in result.stdout
    assert "[1]" in result.stdout
    assert "ci.md :: Quality gates" in result.stdout


def test_cli_reports_when_no_context_matches(tmp_path: Path) -> None:
    guide = tmp_path / "guide.md"
    guide.write_text("# CI\n\nDeterministic tests", encoding="utf-8")

    result = runner.invoke(
        app,
        ["retrieve", "unrelated vocabulary", "--source", str(guide)],
    )

    assert result.exit_code == 0
    assert "No matching context found." in result.stdout


def test_cli_returns_error_for_missing_source(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["retrieve", "quality", "--source", str(tmp_path / "missing")],
    )

    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_cli_answers_with_verified_source_list(tmp_path: Path) -> None:
    guide = tmp_path / "guide.md"
    guide.write_text(
        "# Quality gates\n\nRuff and coverage run before merge.", encoding="utf-8"
    )

    result = runner.invoke(
        app,
        ["answer", "Ruff coverage", "--source", str(guide)],
    )

    assert result.exit_code == 0
    assert "Based on the retrieved documentation:" in result.stdout
    assert "Sources:" in result.stdout
    assert "[1]" in result.stdout
    assert "guide.md :: Quality gates" in result.stdout


def test_cli_answer_abstains_when_evidence_is_missing(tmp_path: Path) -> None:
    guide = tmp_path / "guide.md"
    guide.write_text("# CI\n\nDeterministic tests", encoding="utf-8")

    result = runner.invoke(
        app,
        ["answer", "unrelated vocabulary", "--source", str(guide)],
    )

    assert result.exit_code == 0
    assert "could not find enough evidence" in result.stdout
    assert "Sources:" not in result.stdout
