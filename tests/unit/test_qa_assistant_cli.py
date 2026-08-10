import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

import qa_assistant.cli as cli
from qa_assistant.cli import app
from qa_assistant.generation import INSUFFICIENT_EVIDENCE
from qa_assistant.openai_generator import ReasoningEffort, ResponseUsage

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


def test_cli_exports_dashboard_ready_extractive_evaluation(tmp_path: Path) -> None:
    output = tmp_path / "evaluation.json"

    result = runner.invoke(app, ["evaluate", "--output", str(output)])

    assert result.exit_code == 0
    assert "Evaluation complete: 5/10 cases passed (50.0%)." in result.stdout
    assert "FAIL conflicting-retention:" in result.stdout
    assert "FAIL retrieved-prompt-injection:" in result.stdout
    assert f"Report: {output}" in result.stdout
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["schema_version"] == "2.0"
    assert data["run"]["provider"] == "extractive"
    assert data["run"]["model"] is None
    assert data["run"]["reasoning_effort"] is None
    assert data["summary"]["passed_count"] == 5
    assert data["summary"]["case_count"] == 10
    assert [case["case_id"] for case in data["cases"]] == [
        "supported-merge-checks",
        "unsupported-ownership",
        "conflicting-retention",
        "retrieved-prompt-injection",
        "supported-browser-smoke-test",
        "multi-source-release-gates",
        "partially-relevant-retrieval",
        "lexical-paraphrase-miss",
        "current-over-archived-policy",
        "unsupported-injection-abstention",
    ]


def test_cli_evaluation_can_fail_gate_after_writing_report(tmp_path: Path) -> None:
    output = tmp_path / "evaluation.json"

    result = runner.invoke(
        app,
        ["evaluate", "--output", str(output), "--fail-on-failure"],
    )

    assert result.exit_code == 1
    assert output.is_file()
    assert "Evaluation complete: 5/10 cases passed" in result.stdout


def test_cli_exports_mocked_openai_metadata_and_usage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "openai-evaluation.json"
    generated_questions: list[str] = []
    cases = cli.grounding_evaluation_cases()
    by_id = {case.identifier: case for case in cases}
    responses = {
        by_id["supported-merge-checks"].question: (
            "Ruff and coverage run before merge [1]."
        ),
        by_id["conflicting-retention"].question: INSUFFICIENT_EVIDENCE,
        by_id["supported-browser-smoke-test"].question: (
            "Playwright runs the Chromium checkout smoke test [1]."
        ),
        by_id["multi-source-release-gates"].question: (
            "Playwright and Chromium protect browser checkout [1]. "
            "Ruff and coverage protect code quality [2]."
        ),
        by_id["partially-relevant-retrieval"].question: (
            "Failure screenshots are stored under reports/screenshots [1]."
        ),
        by_id["current-over-archived-policy"].question: (
            "Current policy retains compliance reports for 30 days [1]."
        ),
        by_id["unsupported-injection-abstention"].question: INSUFFICIENT_EVIDENCE,
    }

    class FakeOpenAIGenerator:
        def __init__(
            self,
            *,
            model: str,
            reasoning_effort: ReasoningEffort | str,
            max_output_tokens: int,
        ) -> None:
            self.model = model
            self.reasoning_effort = ReasoningEffort(reasoning_effort)
            self.max_output_tokens = max_output_tokens
            self.last_usage: ResponseUsage | None = None

        def generate(self, request: object) -> str:
            question = request.question
            generated_questions.append(question)
            self.last_usage = ResponseUsage(10, 5, 15, 2)
            return responses[question]

    monkeypatch.setattr(cli, "OpenAIResponsesGenerator", FakeOpenAIGenerator)

    result = runner.invoke(
        app,
        [
            "evaluate",
            "--output",
            str(output),
            "--provider",
            "openai",
            "--model",
            "mock-model",
            "--reasoning-effort",
            "high",
        ],
    )

    assert result.exit_code == 0
    assert "Evaluation complete: 9/10 cases passed" in result.stdout
    assert len(generated_questions) == 8
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["run"]["provider"] == "openai"
    assert data["run"]["model"] == "mock-model"
    assert data["run"]["reasoning_effort"] == "high"
    assert data["cases"][0]["telemetry"]["usage"]["total_tokens"] == 15
    assert data["cases"][1]["telemetry"]["usage"] is None
    assert data["cases"][7]["telemetry"]["usage"] is None


def test_cli_evaluation_reports_export_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_export(report: object, output: Path) -> None:
        raise OSError(f"cannot write {output.name}")

    monkeypatch.setattr(cli, "write_evaluation_report", fail_export)

    result = runner.invoke(
        app,
        ["evaluate", "--output", str(tmp_path / "evaluation.json")],
    )

    assert result.exit_code == 1
    assert "cannot write evaluation.json" in result.output


def test_cli_renders_evaluation_dashboard(tmp_path: Path) -> None:
    report = tmp_path / "evaluation.json"
    output = tmp_path / "dashboard.html"
    evaluation = runner.invoke(app, ["evaluate", "--output", str(report)])

    result = runner.invoke(
        app,
        [
            "dashboard",
            "--report",
            str(report),
            "--output",
            str(output),
        ],
    )

    assert evaluation.exit_code == 0
    assert result.exit_code == 0
    assert f"Dashboard: {output}" in result.stdout
    rendered = output.read_text(encoding="utf-8")
    assert "Grounded RAG quality, made visible." in rendered
    assert 'data-status="failed"' in rendered


def test_cli_dashboard_reports_invalid_input(tmp_path: Path) -> None:
    report = tmp_path / "invalid.json"
    report.write_text('{"schema_version": "9.0"}', encoding="utf-8")

    result = runner.invoke(app, ["dashboard", "--report", str(report)])

    assert result.exit_code == 1
    assert "unsupported evaluation report schema_version" in result.output
