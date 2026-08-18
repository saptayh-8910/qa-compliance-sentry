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


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """Separated instructions, question, and untrusted retrieved evidence."""

    instructions: str
    question: str
    context: RetrievalContext


@dataclass(frozen=True, slots=True)
class GenerationUsage:
    """Provider-neutral token counts when an answer service reports them."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    reasoning_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class AnswerCitation:
    """One validated citation used by a grounded answer."""

    identifier: int
    source: str
    heading: str

    @property
    def label(self) -> str:
        return f"[{self.identifier}] {self.source} :: {self.heading}"


@dataclass(frozen=True, slots=True)
class GroundedAnswer:
    """A generated or abstaining answer with verified source references."""

    question: str
    text: str
    citations: tuple[AnswerCitation, ...]
    context: RetrievalContext

    @property
    def is_supported(self) -> bool:
        return bool(self.citations)
