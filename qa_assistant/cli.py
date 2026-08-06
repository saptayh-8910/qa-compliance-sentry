"""Command-line access to deterministic QA document retrieval."""

from __future__ import annotations

from pathlib import Path

import typer

from qa_assistant.assistant import QAAssistant
from qa_assistant.generation import ExtractiveGenerator
from qa_assistant.service import QAKnowledgeBase

DEFAULT_SOURCES = (Path("README.md"), Path("docs"))

app = typer.Typer(
    name="qa-assistant",
    help="Retrieve citation-labelled context from local QA documentation.",
)


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
) -> None:
    """Answer with the deterministic extractive baseline and verified citations."""
    selected_sources = sources or list(DEFAULT_SOURCES)
    try:
        knowledge_base = QAKnowledgeBase.from_paths(
            selected_sources,
            max_chunk_chars=max_chunk_chars,
        )
        assistant = QAAssistant(
            knowledge_base,
            ExtractiveGenerator(max_chars=max_answer_chars),
        )
        grounded_answer = assistant.answer(
            question,
            top_k=top,
            max_context_chars=max_context_chars,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(grounded_answer.text)
    if grounded_answer.citations:
        typer.echo("Sources:")
        for citation in grounded_answer.citations:
            typer.echo(citation.label)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
