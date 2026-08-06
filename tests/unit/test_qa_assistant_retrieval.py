from pathlib import Path

import pytest

from qa_assistant.models import DocumentChunk
from qa_assistant.retrieval import LexicalRetriever, build_context, tokenize
from qa_assistant.service import QAKnowledgeBase


@pytest.fixture
def chunks() -> tuple[DocumentChunk, ...]:
    return (
        DocumentChunk(
            source="docs/ci.md",
            heading="Quality gates",
            text="Deterministic tests enforce branch coverage before merge.",
            position=0,
        ),
        DocumentChunk(
            source="docs/browser.md",
            heading="Playwright",
            text="Chromium exercises the external checkout journey.",
            position=0,
        ),
        DocumentChunk(
            source="docs/data.md",
            heading="Database validation",
            text="SQLite checks duplicate and orphaned records.",
            position=0,
        ),
    )


def test_tokenize_normalizes_case_and_punctuation() -> None:
    assert tokenize("How does CI/CD use Quality-Gates?") == (
        "ci",
        "cd",
        "quality",
        "gates",
    )


def test_retriever_ranks_relevant_heading_and_body_terms(
    chunks: tuple[DocumentChunk, ...],
) -> None:
    results = LexicalRetriever(chunks).search("deterministic quality coverage", top_k=2)

    assert results[0].chunk.source == "docs/ci.md"
    assert results[0].score > 0
    assert len(results) == 1


def test_retriever_returns_empty_results_for_unknown_terms(
    chunks: tuple[DocumentChunk, ...],
) -> None:
    assert LexicalRetriever(chunks).search("unrelated vocabulary") == ()


def test_retriever_ignores_common_words_in_natural_questions() -> None:
    chunks = (
        DocumentChunk(
            "history.md",
            "Project history",
            "How the project changed and why it was built.",
            0,
        ),
        DocumentChunk(
            "ci.md",
            "Continuous integration",
            "Ruff and branch-aware coverage run in CI.",
            0,
        ),
    )

    results = LexicalRetriever(chunks).search(
        "How does CI use Ruff and branch-aware coverage?"
    )

    assert results[0].chunk.source == "ci.md"


def test_retriever_uses_stable_source_order_for_score_ties() -> None:
    tied = (
        DocumentChunk("z.md", "Same", "shared term", 0),
        DocumentChunk("a.md", "Same", "shared term", 0),
    )

    results = LexicalRetriever(tied).search("shared")

    assert [result.chunk.source for result in results] == ["a.md", "z.md"]


@pytest.mark.parametrize(
    ("query", "top_k", "message"),
    [
        ("quality", 0, "top_k"),
        ("---", 1, "searchable term"),
    ],
)
def test_retriever_rejects_invalid_search_options(
    chunks: tuple[DocumentChunk, ...], query: str, top_k: int, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        LexicalRetriever(chunks).search(query, top_k=top_k)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"k1": 0}, "k1"),
        ({"b": 1.1}, "between"),
    ],
)
def test_retriever_rejects_invalid_ranker_configuration(
    chunks: tuple[DocumentChunk, ...], kwargs: dict[str, float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        LexicalRetriever(chunks, **kwargs)


def test_retriever_rejects_chunks_without_searchable_terms() -> None:
    with pytest.raises(ValueError, match="searchable terms"):
        LexicalRetriever((DocumentChunk("---", "---", "---", 0),))


def test_build_context_numbers_citations_and_respects_budget(
    chunks: tuple[DocumentChunk, ...],
) -> None:
    context = build_context(
        LexicalRetriever(chunks),
        "quality deterministic",
        max_chars=100,
    )

    assert context.results[0].chunk.citation == "docs/ci.md :: Quality gates"
    assert context.text.startswith("[1] docs/ci.md :: Quality gates")
    assert len(context.text) <= 100


def test_build_context_rejects_tiny_budget(chunks: tuple[DocumentChunk, ...]) -> None:
    with pytest.raises(ValueError, match="at least 100"):
        build_context(LexicalRetriever(chunks), "quality", max_chars=99)


def test_knowledge_base_indexes_paths_and_exposes_cited_context(
    tmp_path: Path,
) -> None:
    guide = tmp_path / "guide.md"
    guide.write_text(
        "# Test isolation\n\nMock external APIs for deterministic unit tests.",
        encoding="utf-8",
    )

    knowledge_base = QAKnowledgeBase.from_paths([guide], base_dir=tmp_path)
    context = knowledge_base.context("mock deterministic")

    assert knowledge_base.document_count == 1
    assert len(knowledge_base.chunks) == 1
    assert "guide.md :: Test isolation" in context.text


def test_knowledge_base_rejects_documents_without_searchable_text(
    tmp_path: Path,
) -> None:
    blank = tmp_path / "blank.md"
    blank.write_text("\n", encoding="utf-8")

    with pytest.raises(ValueError, match="searchable text"):
        QAKnowledgeBase.from_paths([blank])
