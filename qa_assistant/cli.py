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
from qa_assistant.evaluation import evaluate_case, grounding_evaluation_cases
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
    """Build deterministic context for the Stage 3 QA assistant."""


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
        help="Generator under evaluation; openai makes three paid API requests",
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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
