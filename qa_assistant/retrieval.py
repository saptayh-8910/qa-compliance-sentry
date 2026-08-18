"""Small deterministic BM25-style retriever for local QA documentation."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence

from qa_assistant.models import DocumentChunk, RetrievalContext, SearchResult

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "does",
        "for",
        "from",
        "give",
        "how",
        "in",
        "into",
        "is",
        "it",
        "me",
        "of",
        "on",
        "or",
        "that",
        "tell",
        "the",
        "this",
        "to",
        "use",
        "was",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
    }
)
_OVERVIEW_SUBJECT_TERMS = frozenset(
    {"application", "document", "platform", "product", "project", "service", "system"}
)
_OVERVIEW_INTENT_TERMS = frozenset(
    {
        "about",
        "describe",
        "description",
        "do",
        "goals",
        "introduction",
        "overview",
        "problem",
        "purpose",
        "solve",
        "summarize",
        "summary",
    }
)
_OVERVIEW_HEADING_TERMS = frozenset(
    {
        "about",
        "background",
        "description",
        "goals",
        "introduction",
        "overview",
        "problem",
        "purpose",
        "summary",
    }
)


def tokenize(text: str) -> tuple[str, ...]:
    """Normalize text into deterministic lowercase search terms."""
    return tuple(
        token for token in _TOKEN.findall(text.lower()) if token not in _STOP_WORDS
    )


def is_overview_query(query: str) -> bool:
    """Identify bounded requests for a whole-document introduction or purpose."""
    terms = set(tokenize(query))
    if not terms.intersection(_OVERVIEW_SUBJECT_TERMS):
        return False
    allowed = _OVERVIEW_SUBJECT_TERMS | _OVERVIEW_INTENT_TERMS
    return len(terms) <= 5 and terms.issubset(allowed)


class LexicalRetriever:
    """Rank chunks with BM25 term frequency and document-frequency scoring."""

    def __init__(
        self,
        chunks: Sequence[DocumentChunk],
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        if not chunks:
            raise ValueError("at least one non-empty document chunk is required")
        if k1 <= 0:
            raise ValueError("k1 must be positive")
        if not 0 <= b <= 1:
            raise ValueError("b must be between 0 and 1")

        self.chunks = tuple(chunks)
        self.k1 = k1
        self.b = b
        self._term_counts = tuple(
            Counter(tokenize(f"{chunk.heading} {chunk.text}")) for chunk in chunks
        )
        self._lengths = tuple(sum(counts.values()) for counts in self._term_counts)
        self._average_length = sum(self._lengths) / len(self._lengths)
        if self._average_length == 0:
            raise ValueError("document chunks must include searchable terms")
        self._document_frequency = Counter(
            term for counts in self._term_counts for term in counts
        )

    def search(self, query: str, *, top_k: int = 3) -> tuple[SearchResult, ...]:
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        query_terms = Counter(tokenize(query))
        if not query_terms:
            raise ValueError("query must include at least one searchable term")

        total_chunks = len(self.chunks)
        base_scores: list[float] = []
        for _chunk, counts, length in zip(
            self.chunks, self._term_counts, self._lengths, strict=True
        ):
            score = 0.0
            for term, query_frequency in query_terms.items():
                term_frequency = counts.get(term, 0)
                if not term_frequency:
                    continue
                document_frequency = self._document_frequency[term]
                inverse_frequency = math.log(
                    1
                    + (total_chunks - document_frequency + 0.5)
                    / (document_frequency + 0.5)
                )
                normalization = term_frequency + self.k1 * (
                    1 - self.b + self.b * length / self._average_length
                )
                score += (
                    query_frequency
                    * inverse_frequency
                    * term_frequency
                    * (self.k1 + 1)
                    / normalization
                )
            base_scores.append(score)

        scored: list[SearchResult] = []
        if is_overview_query(query):
            highest_base = max(base_scores, default=0.0) or 1.0
            for chunk, score in zip(self.chunks, base_scores, strict=True):
                heading_terms = set(tokenize(chunk.heading))
                heading_matches = len(
                    heading_terms.intersection(_OVERVIEW_HEADING_TERMS)
                )
                if heading_matches:
                    score += highest_base * 3 + heading_matches
                if chunk.position == 0:
                    score += highest_base * 2
                if score > 0:
                    scored.append(SearchResult(chunk=chunk, score=score))
        else:
            scored = [
                SearchResult(chunk=chunk, score=score)
                for chunk, score in zip(self.chunks, base_scores, strict=True)
                if score > 0
            ]

        scored.sort(
            key=lambda result: (
                -result.score,
                result.chunk.source,
                result.chunk.position,
            )
        )
        return tuple(scored[:top_k])


def build_context(
    retriever: LexicalRetriever,
    query: str,
    *,
    top_k: int = 3,
    max_chars: int = 4_000,
) -> RetrievalContext:
    """Render ranked chunks into a bounded, numbered citation context."""
    if max_chars < 100:
        raise ValueError("max_chars must be at least 100")

    ranked = retriever.search(query, top_k=top_k)
    return build_context_from_results(query, ranked, max_chars=max_chars)


def build_context_from_results(
    query: str,
    ranked: Sequence[SearchResult],
    *,
    max_chars: int = 4_000,
) -> RetrievalContext:
    """Render already-ranked results into bounded, numbered citation context."""
    if max_chars < 100:
        raise ValueError("max_chars must be at least 100")

    selected: list[SearchResult] = []
    blocks: list[str] = []
    used = 0
    for result in ranked:
        number = len(selected) + 1
        header = f"[{number}] {result.chunk.citation}\n"
        separator = "\n\n" if blocks else ""
        available = max_chars - used - len(separator) - len(header)
        if available <= 0:
            break
        body = result.chunk.text
        if len(body) > available:
            if blocks:
                break
            body = body[:available].rstrip()
        blocks.append(f"{header}{body}")
        selected.append(result)
        used += len(separator) + len(blocks[-1])
        if len(body) < len(result.chunk.text):
            break

    return RetrievalContext(
        query=query,
        results=tuple(selected),
        text="\n\n".join(blocks),
    )
