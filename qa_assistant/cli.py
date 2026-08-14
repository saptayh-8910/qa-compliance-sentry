"""Command-line access to deterministic QA document retrieval."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import typer
from dotenv import load_dotenv

from qa_assistant.assistant import QAAssistant
from qa_assistant.benchmark_dashboard import (
    BenchmarkDashboardDataError,
    write_benchmark_dashboard,
)
from qa_assistant.benchmarking import (
    BenchmarkMetadata,
    BenchmarkReport,
    BenchmarkSample,
    write_benchmark_report,
)
from qa_assistant.dashboard import DashboardDataError, write_dashboard
from qa_assistant.evaluation import evaluate_case, grounding_evaluation_cases
from qa_assistant.faithfulness import (
    DeterministicFaithfulnessJudge,
    validate_faithfulness_judge,
)
from qa_assistant.faithfulness_dashboard import (
    FaithfulnessDashboardDataError,
    write_faithfulness_dashboard,
)
from qa_assistant.faithfulness_reporting import (
    faithfulness_report_data,
    write_faithfulness_report,
)
from qa_assistant.generation import AnswerGenerator, ExtractiveGenerator
from qa_assistant.models import GroundedAnswer
from qa_assistant.openai_generator import (
    DEFAULT_OPENAI_MODEL,
    DEFAULT_REASONING_EFFORT,
    OpenAIAdapterError,
    OpenAIResponsesGenerator,
    ReasoningEffort,
    ResponseUsage,
)
from qa_assistant.reporting import (
    EvaluationObservation,
    EvaluationReport,
    EvaluationRunMetadata,
    write_evaluation_report,
)
from qa_assistant.service import QAKnowledgeBase
from qa_assistant.workspace import WorkspaceDataError, run_workspace

DEFAULT_SOURCES = (Path("README.md"), Path("docs"))

app = typer.Typer(
    name="qa-assistant",
    help="Retrieve citation-labelled context from local QA documentation.",
)


class AnswerProvider(StrEnum):
    """Available answer-generation implementations."""

    EXTRACTIVE = "extractive"
    OPENAI = "openai"


def _answer_generator(
    provider: AnswerProvider,
    *,
    max_answer_chars: int,
    model: str | None,
    reasoning_effort: ReasoningEffort | None,
    max_output_tokens: int,
) -> AnswerGenerator:
    if provider is AnswerProvider.EXTRACTIVE:
        return ExtractiveGenerator(max_chars=max_answer_chars)

    load_dotenv()
    selected_model = model or os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    selected_effort = (
        reasoning_effort.value
        if reasoning_effort is not None
        else os.getenv("OPENAI_REASONING_EFFORT", DEFAULT_REASONING_EFFORT.value)
    )
    return OpenAIResponsesGenerator(
        model=selected_model,
        reasoning_effort=selected_effort,
        max_output_tokens=max_output_tokens,
    )


def _build_assistant(
    sources: list[Path],
    *,
    max_chunk_chars: int,
    provider: AnswerProvider,
    max_answer_chars: int,
    model: str | None,
    reasoning_effort: ReasoningEffort | None,
    max_output_tokens: int,
) -> QAAssistant:
    knowledge_base = QAKnowledgeBase.from_paths(
        sources,
        max_chunk_chars=max_chunk_chars,
    )
    return QAAssistant(
        knowledge_base,
        _answer_generator(
            provider,
            max_answer_chars=max_answer_chars,
            model=model,
            reasoning_effort=reasoning_effort,
            max_output_tokens=max_output_tokens,
        ),
    )


def _echo_grounded_answer(grounded_answer: GroundedAnswer) -> None:
    typer.echo(grounded_answer.text)
    if grounded_answer.citations:
        typer.echo("Sources:")
        for citation in grounded_answer.citations:
            typer.echo(citation.label)


def _report_configuration(
    generator: AnswerGenerator,
) -> tuple[str | None, str | None]:
    if not isinstance(generator, OpenAIResponsesGenerator):
        return None, None
    return generator.model, generator.reasoning_effort.value


@app.callback()
def root() -> None:
    """Run grounded QA, evaluation, and reporting workflows."""


@app.command("retrieve")
def retrieve(
    query: str = typer.Argument(..., help="Question or search terms"),
    sources: list[Path] | None = typer.Option(
        None,
        "--source",
        "-s",
        help="Document file or directory; repeat to add sources",
    ),
    top: int = typer.Option(3, "--top", "-k", min=1),
    max_chunk_chars: int = typer.Option(1_200, "--max-chunk-chars", min=100),
    max_context_chars: int = typer.Option(4_000, "--max-context-chars", min=100),
) -> None:
    """Index local documents and print the most relevant cited context."""
    selected_sources = sources or list(DEFAULT_SOURCES)
    try:
        knowledge_base = QAKnowledgeBase.from_paths(
            selected_sources,
            max_chunk_chars=max_chunk_chars,
        )
        context = knowledge_base.context(
            query,
            top_k=top,
            max_chars=max_context_chars,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"Indexed {knowledge_base.document_count} documents into "
        f"{len(knowledge_base.chunks)} chunks."
    )
    if not context.results:
        typer.echo("No matching context found.")
        return
    typer.echo(context.text)


@app.command("answer")
def answer(
    question: str = typer.Argument(..., help="Question about the indexed QA docs"),
    sources: list[Path] | None = typer.Option(
        None,
        "--source",
        "-s",
        help="Document file or directory; repeat to add sources",
    ),
    top: int = typer.Option(3, "--top", "-k", min=1),
    max_chunk_chars: int = typer.Option(1_200, "--max-chunk-chars", min=100),
    max_context_chars: int = typer.Option(4_000, "--max-context-chars", min=100),
    max_answer_chars: int = typer.Option(500, "--max-answer-chars", min=80),
    provider: AnswerProvider = typer.Option(
        AnswerProvider.EXTRACTIVE,
        "--provider",
        help="Answer generator; openai makes an external paid API request",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="OpenAI model override (or set OPENAI_MODEL)",
    ),
    reasoning_effort: ReasoningEffort | None = typer.Option(
        None,
        "--reasoning-effort",
        help="OpenAI reasoning level (or set OPENAI_REASONING_EFFORT)",
    ),
    max_output_tokens: int = typer.Option(
        600,
        "--max-output-tokens",
        min=1,
        help="Maximum output tokens for the OpenAI provider",
    ),
) -> None:
    """Answer with an explicit provider and verified numeric citations."""
    selected_sources = sources or list(DEFAULT_SOURCES)
    try:
        assistant = _build_assistant(
            selected_sources,
            max_chunk_chars=max_chunk_chars,
            provider=provider,
            max_answer_chars=max_answer_chars,
            model=model,
            reasoning_effort=reasoning_effort,
            max_output_tokens=max_output_tokens,
        )
        grounded_answer = assistant.answer(
            question,
            top_k=top,
            max_context_chars=max_context_chars,
        )
    except (OSError, UnicodeError, ValueError, OpenAIAdapterError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    _echo_grounded_answer(grounded_answer)


@app.command("chat")
def chat(
    sources: list[Path] | None = typer.Option(
        None,
        "--source",
        "-s",
        help="Document file or directory; repeat to add sources",
    ),
    top: int = typer.Option(3, "--top", "-k", min=1),
    max_chunk_chars: int = typer.Option(1_200, "--max-chunk-chars", min=100),
    max_context_chars: int = typer.Option(4_000, "--max-context-chars", min=100),
    max_answer_chars: int = typer.Option(500, "--max-answer-chars", min=80),
    provider: AnswerProvider = typer.Option(
        AnswerProvider.EXTRACTIVE,
        "--provider",
        help="Answer generator; openai charges for each supported turn",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="OpenAI model override (or set OPENAI_MODEL)",
    ),
    reasoning_effort: ReasoningEffort | None = typer.Option(
        None,
        "--reasoning-effort",
        help="OpenAI reasoning level (or set OPENAI_REASONING_EFFORT)",
    ),
    max_output_tokens: int = typer.Option(
        600,
        "--max-output-tokens",
        min=1,
        help="Maximum output tokens for each OpenAI response",
    ),
) -> None:
    """Ask multiple questions against one indexed documentation session."""
    selected_sources = sources or list(DEFAULT_SOURCES)
    try:
        assistant = _build_assistant(
            selected_sources,
            max_chunk_chars=max_chunk_chars,
            provider=provider,
            max_answer_chars=max_answer_chars,
            model=model,
            reasoning_effort=reasoning_effort,
            max_output_tokens=max_output_tokens,
        )
    except (OSError, UnicodeError, ValueError, OpenAIAdapterError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    knowledge_base = assistant.knowledge_base
    typer.echo(
        f"Chat ready: indexed {knowledge_base.document_count} documents into "
        f"{len(knowledge_base.chunks)} chunks."
    )
    typer.echo("Ask a question, or type 'exit' or 'quit' to end the session.")

    while True:
        try:
            question = typer.prompt("You", default="", show_default=False).strip()
        except (EOFError, typer.Abort):
            typer.echo("Chat ended.")
            return

        if question.casefold() in {"exit", "quit"}:
            typer.echo("Chat ended.")
            return
        if not question:
            typer.echo("Please enter a question.")
            continue

        try:
            grounded_answer = assistant.answer(
                question,
                top_k=top,
                max_context_chars=max_context_chars,
            )
        except (OSError, UnicodeError, ValueError, OpenAIAdapterError) as exc:
            typer.echo(f"Unable to answer: {exc}", err=True)
            continue

        typer.echo("Assistant:")
        _echo_grounded_answer(grounded_answer)


@app.command("workspace")
def workspace(
    port: int = typer.Option(
        8765,
        "--port",
        min=1,
        max=65_535,
        help="Localhost port for the real-data browser workspace",
    ),
    open_browser: bool = typer.Option(
        True,
        "--open-browser/--no-open-browser",
        help="Open the workspace in the default browser after starting",
    ),
) -> None:
    """Upload documents and inspect labelled retrieval performance locally."""
    try:
        run_workspace(port=port, open_browser=open_browser)
    except (OSError, WorkspaceDataError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


@app.command("evaluate")
def evaluate(
    output: Path = typer.Option(
        Path("reports/rag-evaluation.json"),
        "--output",
        "-o",
        help="Destination for the versioned JSON report",
    ),
    provider: AnswerProvider = typer.Option(
        AnswerProvider.EXTRACTIVE,
        "--provider",
        help="Generator under evaluation; openai makes eight paid API requests",
    ),
    max_answer_chars: int = typer.Option(500, "--max-answer-chars", min=80),
    model: str | None = typer.Option(
        None,
        "--model",
        help="OpenAI model override (or set OPENAI_MODEL)",
    ),
    reasoning_effort: ReasoningEffort | None = typer.Option(
        None,
        "--reasoning-effort",
        help="OpenAI reasoning level (or set OPENAI_REASONING_EFFORT)",
    ),
    max_output_tokens: int = typer.Option(
        600,
        "--max-output-tokens",
        min=1,
        help="Maximum output tokens for each OpenAI response",
    ),
    fail_on_failure: bool = typer.Option(
        False,
        "--fail-on-failure",
        help="Return exit code 1 after writing the report when any case fails",
    ),
) -> None:
    """Run the fixed grounding rubric and export dashboard-ready JSON."""
    try:
        generator = _answer_generator(
            provider,
            max_answer_chars=max_answer_chars,
            model=model,
            reasoning_effort=reasoning_effort,
            max_output_tokens=max_output_tokens,
        )
        selected_model, selected_effort = _report_configuration(generator)
        observations: list[EvaluationObservation] = []
        for case in grounding_evaluation_cases():
            if isinstance(generator, OpenAIResponsesGenerator):
                generator.last_usage = None
            started = perf_counter()
            result = evaluate_case(case, generator)
            duration = round(perf_counter() - started, 6)
            usage = getattr(generator, "last_usage", None)
            observations.append(
                EvaluationObservation(
                    result=result,
                    duration_seconds=duration,
                    usage=usage if isinstance(usage, ResponseUsage) else None,
                )
            )

        report = EvaluationReport(
            metadata=EvaluationRunMetadata(
                run_id=str(uuid4()),
                created_at=datetime.now(UTC),
                provider=provider.value,
                model=selected_model,
                reasoning_effort=selected_effort,
            ),
            observations=tuple(observations),
        )
        write_evaluation_report(report, output)
    except (OSError, UnicodeError, ValueError, OpenAIAdapterError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    summary = report.summary
    typer.echo(
        f"Evaluation complete: {summary.passed_count}/{summary.case_count} "
        f"cases passed ({summary.pass_rate:.1%})."
    )
    for observation in report.observations:
        if not observation.result.passed:
            typer.echo(
                f"FAIL {observation.result.case_id}: "
                f"{observation.result.failure_summary}"
            )
    typer.echo(f"Report: {output}")
    if fail_on_failure and summary.passed_count != summary.case_count:
        raise typer.Exit(code=1)


@app.command("dashboard")
def dashboard(
    report: Path = typer.Option(
        Path("reports/rag-evaluation.json"),
        "--report",
        "-r",
        help="Version 2 or legacy version 1 evaluation JSON to visualize",
    ),
    output: Path = typer.Option(
        Path("reports/rag-dashboard.html"),
        "--output",
        "-o",
        help="Destination for the standalone HTML dashboard",
    ),
) -> None:
    """Render a safe local dashboard from a supported evaluation report."""
    try:
        write_dashboard(report, output)
    except (OSError, UnicodeError, DashboardDataError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Dashboard: {output}")


@app.command("benchmark")
def benchmark(
    output: Path = typer.Option(
        Path("reports/rag-benchmark.json"),
        "--output",
        "-o",
        help="Destination for the repeated-run benchmark JSON",
    ),
    repetitions: int = typer.Option(
        3,
        "--repetitions",
        min=2,
        max=100,
        help="Number of times to repeat every evaluation case",
    ),
    provider: AnswerProvider = typer.Option(
        AnswerProvider.EXTRACTIVE,
        "--provider",
        help="Generator under benchmark; OpenAI can create paid API usage",
    ),
    confirm_paid: bool = typer.Option(
        False,
        "--confirm-paid",
        help="Explicitly allow the projected paid OpenAI benchmark calls",
    ),
    max_answer_chars: int = typer.Option(500, "--max-answer-chars", min=80),
    model: str | None = typer.Option(None, "--model", help="OpenAI model override"),
    reasoning_effort: ReasoningEffort | None = typer.Option(
        None, "--reasoning-effort", help="OpenAI reasoning level"
    ),
    max_output_tokens: int = typer.Option(
        600, "--max-output-tokens", min=1, help="Maximum tokens per OpenAI response"
    ),
) -> None:
    """Repeat the grounding rubric and summarize stability and latency."""
    paid_calls = repetitions * 8
    if provider is AnswerProvider.OPENAI and not confirm_paid:
        typer.echo(
            "OpenAI benchmarking is blocked until --confirm-paid is supplied; "
            f"this configuration can make {paid_calls} paid API requests.",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        generator = _answer_generator(
            provider,
            max_answer_chars=max_answer_chars,
            model=model,
            reasoning_effort=reasoning_effort,
            max_output_tokens=max_output_tokens,
        )
        selected_model, selected_effort = _report_configuration(generator)
        samples: list[BenchmarkSample] = []
        for iteration in range(1, repetitions + 1):
            for case in grounding_evaluation_cases():
                if isinstance(generator, OpenAIResponsesGenerator):
                    generator.last_usage = None
                started = perf_counter()
                result = evaluate_case(case, generator)
                duration = round(perf_counter() - started, 6)
                usage = getattr(generator, "last_usage", None)
                samples.append(
                    BenchmarkSample(
                        iteration=iteration,
                        result=result,
                        duration_seconds=duration,
                        usage=usage if isinstance(usage, ResponseUsage) else None,
                    )
                )
        report = BenchmarkReport(
            metadata=BenchmarkMetadata(
                benchmark_id=str(uuid4()),
                created_at=datetime.now(UTC),
                provider=provider.value,
                model=selected_model,
                reasoning_effort=selected_effort,
                repetitions=repetitions,
            ),
            samples=tuple(samples),
        )
        write_benchmark_report(report, output)
    except (OSError, UnicodeError, ValueError, OpenAIAdapterError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    summary = report.summary
    typer.echo(
        f"Benchmark complete: {summary.passed_sample_count}/{summary.sample_count} "
        f"samples passed ({summary.sample_pass_rate:.1%}); "
        f"{summary.stable_case_count}/{summary.case_count} cases kept the same "
        f"verdict; {summary.response_stable_case_count}/{summary.case_count} "
        "kept the same answer and citations."
    )
    typer.echo(
        f"Latency: p50 {summary.latency.p50_seconds * 1000:.2f} ms; "
        f"p95 {summary.latency.p95_seconds * 1000:.2f} ms."
    )
    typer.echo(f"Benchmark report: {output}")


@app.command("benchmark-dashboard")
def benchmark_dashboard(
    report: Path = typer.Option(
        Path("reports/rag-benchmark.json"),
        "--report",
        "-r",
        help="Repeated-run benchmark JSON to visualize",
    ),
    output: Path = typer.Option(
        Path("reports/rag-benchmark.html"),
        "--output",
        "-o",
        help="Destination for the standalone benchmark dashboard",
    ),
) -> None:
    """Render repeated latency and stability evidence in plain English."""
    try:
        write_benchmark_dashboard(report, output)
    except (OSError, UnicodeError, BenchmarkDashboardDataError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Benchmark dashboard: {output}")


@app.command("faithfulness")
def faithfulness(
    output: Path = typer.Option(
        Path("reports/rag-faithfulness.json"),
        "--output",
        "-o",
        help="Destination for human-labelled judge-validation JSON",
    ),
    fail_if_unvalidated: bool = typer.Option(
        False,
        "--fail-if-unvalidated",
        help="Return exit code 1 after writing evidence when thresholds fail",
    ),
) -> None:
    """Validate a candidate claim judge against version-controlled human labels."""
    try:
        validation = validate_faithfulness_judge(DeterministicFaithfulnessJudge())
        data = faithfulness_report_data(
            validation,
            run_id=str(uuid4()),
            created_at=datetime.now(UTC),
        )
        write_faithfulness_report(data, output)
    except (OSError, UnicodeError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    metrics = validation.metrics
    status = "validated" if validation.validated else "not validated"
    typer.echo(
        f"Faithfulness judge {status}: {metrics.exact_match_count}/"
        f"{metrics.example_count} exact labels ({metrics.accuracy:.1%}); "
        f"unfaithful recall {metrics.unfaithful_recall:.1%}; "
        f"{metrics.false_negative_count} false negatives."
    )
    typer.echo(f"Faithfulness report: {output}")
    if fail_if_unvalidated and not validation.validated:
        raise typer.Exit(code=1)


@app.command("faithfulness-dashboard")
def faithfulness_dashboard(
    report: Path = typer.Option(
        Path("reports/rag-faithfulness.json"),
        "--report",
        "-r",
        help="Human-labelled faithfulness report to visualize",
    ),
    output: Path = typer.Option(
        Path("reports/rag-faithfulness.html"),
        "--output",
        "-o",
        help="Destination for the standalone faithfulness dashboard",
    ),
) -> None:
    """Render claim-level judge validation with plain-English criteria."""
    try:
        write_faithfulness_dashboard(report, output)
    except (OSError, UnicodeError, FaithfulnessDashboardDataError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Faithfulness dashboard: {output}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
