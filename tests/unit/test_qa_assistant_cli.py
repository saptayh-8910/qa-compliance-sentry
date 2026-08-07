from pathlib import Path

import pytest
from typer.testing import CliRunner

import qa_assistant.cli as cli
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


def test_cli_chat_handles_supported_and_unsupported_turns(tmp_path: Path) -> None:
    guide = tmp_path / "guide.md"
    guide.write_text(
        "# Quality gates\n\nRuff and coverage run before merge.", encoding="utf-8"
    )

    result = runner.invoke(
        app,
        ["chat", "--source", str(guide), "--top", "1"],
        input="\nWhat runs before merge?\nphotosynthesis dinosaurs\nquit\n",
    )

    assert result.exit_code == 0
    assert "Chat ready: indexed 1 documents into 1 chunks." in result.stdout
    assert "Please enter a question." in result.stdout
    assert "Based on the retrieved documentation:" in result.stdout
    assert "guide.md :: Quality gates" in result.stdout
    assert "could not find enough evidence" in result.stdout
    assert result.stdout.count("Sources:") == 1
    assert result.stdout.count("Assistant:") == 2
    assert "Chat ended." in result.stdout


def test_cli_chat_returns_error_for_missing_source(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["chat", "--source", str(tmp_path / "missing")],
    )

    assert result.exit_code == 1
    assert "does not exist" in result.output


def test_cli_chat_ends_cleanly_on_end_of_input(tmp_path: Path) -> None:
    guide = tmp_path / "guide.md"
    guide.write_text("# CI\n\nCoverage runs before merge.", encoding="utf-8")

    result = runner.invoke(
        app,
        ["chat", "--source", str(guide)],
        input=None,
    )

    assert result.exit_code == 0
    assert "Chat ended." in result.stdout


def test_cli_chat_reports_invalid_answer_and_keeps_session_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guide = tmp_path / "guide.md"
    guide.write_text("# CI\n\nCoverage runs before merge.", encoding="utf-8")

    class InvalidGenerator:
        def __init__(self, **kwargs: object) -> None:
            pass

        def generate(self, request: object) -> str:
            return "An answer without a citation."

    monkeypatch.setattr(cli, "ExtractiveGenerator", InvalidGenerator)

    result = runner.invoke(
        app,
        ["chat", "--source", str(guide)],
        input="coverage\nquit\n",
    )

    assert result.exit_code == 0
    assert "Unable to answer: generated answer must include a citation" in result.output
    assert "Chat ended." in result.stdout


def test_cli_openai_provider_is_explicit_and_passes_model_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guide = tmp_path / "guide.md"
    guide.write_text(
        "# Quality gates\n\nRuff and coverage run before merge.", encoding="utf-8"
    )
    configuration: dict[str, object] = {}

    class FakeOpenAIGenerator:
        def __init__(self, **kwargs: object) -> None:
            configuration.update(kwargs)

        def generate(self, request: object) -> str:
            return "Ruff and coverage run before merge [1]."

    monkeypatch.setattr(cli, "OpenAIResponsesGenerator", FakeOpenAIGenerator)

    result = runner.invoke(
        app,
        [
            "answer",
            "Ruff coverage",
            "--source",
            str(guide),
            "--provider",
            "openai",
            "--model",
            "test-model",
            "--reasoning-effort",
            "high",
            "--max-output-tokens",
            "123",
        ],
    )

    assert result.exit_code == 0
    assert "Ruff and coverage run before merge [1]." in result.stdout
    assert configuration == {
        "model": "test-model",
        "reasoning_effort": "high",
        "max_output_tokens": 123,
    }


def test_cli_reports_openai_configuration_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    guide = tmp_path / "guide.md"
    guide.write_text("# Quality gates\n\nCoverage runs before merge.", encoding="utf-8")

    class FailingOpenAIGenerator:
        def __init__(self, **kwargs: object) -> None:
            raise cli.OpenAIAdapterError("OpenAI is unavailable")

    monkeypatch.setattr(cli, "OpenAIResponsesGenerator", FailingOpenAIGenerator)

    result = runner.invoke(
        app,
        [
            "answer",
            "coverage",
            "--source",
            str(guide),
            "--provider",
            "openai",
        ],
    )

    assert result.exit_code == 1
    assert "OpenAI is unavailable" in result.output
