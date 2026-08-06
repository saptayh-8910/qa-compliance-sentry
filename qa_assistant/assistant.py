"""Orchestrate retrieval, answer generation, abstention, and citation mapping."""

from __future__ import annotations

from qa_assistant.generation import GROUNDING_INSTRUCTIONS, AnswerGenerator
from qa_assistant.models import (
    AnswerCitation,
    GenerationRequest,
    GroundedAnswer,
)
from qa_assistant.service import QAKnowledgeBase
from qa_assistant.validation import validate_citations

INSUFFICIENT_EVIDENCE = (
    "I could not find enough evidence in the indexed documentation to answer that."
)


class QAAssistant:
    """Run the grounded question-answering flow over one knowledge base."""

    def __init__(
        self,
        knowledge_base: QAKnowledgeBase,
        generator: AnswerGenerator,
    ) -> None:
        self.knowledge_base = knowledge_base
        self.generator = generator

    def answer(
        self,
        question: str,
        *,
        top_k: int = 3,
        max_context_chars: int = 4_000,
    ) -> GroundedAnswer:
        context = self.knowledge_base.context(
            question,
            top_k=top_k,
            max_chars=max_context_chars,
        )
        if not context.results:
            return GroundedAnswer(
                question=question,
                text=INSUFFICIENT_EVIDENCE,
                citations=(),
                context=context,
            )

        request = GenerationRequest(
            instructions=GROUNDING_INSTRUCTIONS,
            question=question,
            context=context,
        )
        generated = self.generator.generate(request).strip()
        identifiers = validate_citations(generated, context)
        citations = tuple(
            AnswerCitation(
                identifier=identifier,
                source=context.results[identifier - 1].chunk.source,
                heading=context.results[identifier - 1].chunk.heading,
            )
            for identifier in identifiers
        )
        return GroundedAnswer(
            question=question,
            text=generated,
            citations=citations,
            context=context,
        )
