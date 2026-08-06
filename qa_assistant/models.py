"""Domain models for document ingestion and citation-aware retrieval."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceDocument:
    """One UTF-8 source document with a stable display path."""

    source: str
    text: str


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    """A searchable section of a source document."""

    source: str
    heading: str
    text: str
    position: int

    @property
    def citation(self) -> str:
        return f"{self.source} :: {self.heading}"


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A ranked document chunk and its lexical relevance score."""

    chunk: DocumentChunk
    score: float


@dataclass(frozen=True, slots=True)
class RetrievalContext:
    """Bounded, citation-labelled context ready for a later generator."""

    query: str
    results: tuple[SearchResult, ...]
    text: str
