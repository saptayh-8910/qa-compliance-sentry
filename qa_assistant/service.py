"""Public application boundary for indexing and retrieving QA documents."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from learning_algorithms.stage3 import LRUCache, Trie
from qa_assistant.ingestion import chunk_documents, load_documents
from qa_assistant.models import (
    DocumentChunk,
    RetrievalContext,
    SearchResult,
    SourceDocument,
)
from qa_assistant.retrieval import LexicalRetriever, build_context_from_results


class QAKnowledgeBase:
    """In-memory document index used by the Stage 3 assistant."""

    def __init__(
        self,
        chunks: tuple[DocumentChunk, ...],
        *,
        document_count: int,
        search_cache_capacity: int = 128,
    ) -> None:
        self.chunks = chunks
        self.document_count = document_count
        self._retriever = LexicalRetriever(chunks)
        self._search_cache: LRUCache[tuple[str, int], tuple[SearchResult, ...]] = (
            LRUCache(search_cache_capacity)
        )
        self._source_index = Trie()
        for source in sorted({chunk.source for chunk in chunks}):
            self._source_index.insert(source)

    @classmethod
    def from_paths(
        cls,
        sources: Iterable[Path],
        *,
        max_chunk_chars: int = 1_200,
        base_dir: Path | None = None,
        search_cache_capacity: int = 128,
    ) -> QAKnowledgeBase:
        documents = load_documents(sources, base_dir=base_dir)
        return cls.from_documents(
            documents,
            max_chunk_chars=max_chunk_chars,
            search_cache_capacity=search_cache_capacity,
        )

    @classmethod
    def from_documents(
        cls,
        documents: Iterable[SourceDocument],
        *,
        max_chunk_chars: int = 1_200,
        search_cache_capacity: int = 128,
    ) -> QAKnowledgeBase:
        """Build an index from already-loaded or browser-uploaded documents."""
        loaded_documents = tuple(documents)
        if not loaded_documents:
            raise ValueError("at least one document is required")
        chunks = chunk_documents(loaded_documents, max_chars=max_chunk_chars)
        if not chunks:
            raise ValueError("document sources did not contain searchable text")
        return cls(
            chunks,
            document_count=len(loaded_documents),
            search_cache_capacity=search_cache_capacity,
        )

    def search(self, query: str, *, top_k: int = 3) -> tuple[SearchResult, ...]:
        cache_key = (query, top_k)
        cached = self._search_cache.get(cache_key)
        if cached is not None:
            return cached
        results = self._retriever.search(query, top_k=top_k)
        self._search_cache.put(cache_key, results)
        return results

    def sources_with_prefix(
        self,
        prefix: str,
        *,
        limit: int | None = None,
    ) -> tuple[str, ...]:
        """Return indexed source paths beginning with an exact prefix."""
        return self._source_index.words_with_prefix(prefix, limit=limit)

    def context(
        self,
        query: str,
        *,
        top_k: int = 3,
        max_chars: int = 4_000,
    ) -> RetrievalContext:
        return build_context_from_results(
            query,
            self.search(query, top_k=top_k),
            max_chars=max_chars,
        )
