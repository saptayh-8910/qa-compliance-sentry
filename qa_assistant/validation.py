"""Fail-closed validation for generated citation identifiers."""

from __future__ import annotations

import re

from qa_assistant.models import RetrievalContext

_CITATION = re.compile(r"\[(-?\d+)]")


class CitationValidationError(ValueError):
    """Raised when generated text is empty, uncited, or mis-cited."""


def validate_citations(answer: str, context: RetrievalContext) -> tuple[int, ...]:
    """Return unique citation IDs after checking them against retrieved results."""
    if not answer.strip():
        raise CitationValidationError("generated answer cannot be empty")

    identifiers = [int(match) for match in _CITATION.findall(answer)]
    if not identifiers:
        raise CitationValidationError("generated answer must include a citation")

    available = len(context.results)
    invalid = sorted(
        {identifier for identifier in identifiers if not 1 <= identifier <= available}
    )
    if invalid:
        values = ", ".join(str(identifier) for identifier in invalid)
        raise CitationValidationError(f"unknown citation identifier(s): {values}")
    return tuple(dict.fromkeys(identifiers))
