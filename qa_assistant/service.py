"""Public application boundary for indexing and retrieving QA documents."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from qa_assistant.ingestion import chunk_documents, load_documents
from qa_assistant.models import DocumentChunk, RetrievalContext, SearchResult
from qa_assistant.retrieval import LexicalRetriever, build_context


class QAKnowledgeBase:
    """In-memory document index used by the Stage 3 assistant."""

    def __init__(
        self, chunks: tuple[DocumentChunk, ...], *, document_count: int
    ) -> None:
        self.chunks = chunks
        self.document_count = document_count
        self._retriever = LexicalRetriever(chunks)

    @classmethod
    def from_paths(
        cls,
        sources: Iterable[Path],
        *,
        max_chunk_chars: int = 1_200,
        base_dir: Path | None = None,
    ) -> QAKnowledgeBase:
        documents = load_documents(sources, base_dir=base_dir)
        chunks = chunk_documents(documents, max_chars=max_chunk_chars)
        if not chunks:
            raise ValueError("document sources did not contain searchable text")
        return cls(chunks, document_count=len(documents))

    def search(self, query: str, *, top_k: int = 3) -> tuple[SearchResult, ...]:
        return self._retriever.search(query, top_k=top_k)

    def context(
        self,
        query: str,
        *,
        top_k: int = 3,
        max_chars: int = 4_000,
    ) -> RetrievalContext:
        return build_context(
            self._retriever,
            query,
            top_k=top_k,
            max_chars=max_chars,
        )
