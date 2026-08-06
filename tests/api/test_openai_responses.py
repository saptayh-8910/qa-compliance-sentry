from __future__ import annotations

import os
from collections.abc import Callable

import pytest

from qa_assistant.assistant import QAAssistant
from qa_assistant.models import DocumentChunk
from qa_assistant.openai_generator import OpenAIResponsesGenerator, ReasoningEffort
from qa_assistant.service import QAKnowledgeBase

pytestmark = [pytest.mark.api, pytest.mark.external, pytest.mark.ai]


@pytest.mark.skipif(
    os.getenv("RUN_OPENAI_LIVE_TESTS") != "1",
    reason="set RUN_OPENAI_LIVE_TESTS=1 to allow two paid OpenAI API calls",
)
@pytest.mark.parametrize(
    ("model", "reasoning_effort"),
    [
        pytest.param("gpt-5.6-sol", ReasoningEffort.MEDIUM, id="sol-medium"),
        pytest.param("gpt-5.6-luna", ReasoningEffort.HIGH, id="luna-high"),
    ],
)
def test_openai_grounded_answer_live(
    model: str,
    reasoning_effort: ReasoningEffort,
    record_property: Callable[[str, object], None],
) -> None:
    chunk = DocumentChunk(
        source="quality-guide.md",
        heading="Merge checks",
        text="Ruff and branch-aware coverage run before a pull request is merged.",
        position=0,
    )
    knowledge_base = QAKnowledgeBase((chunk,), document_count=1)
    assistant = QAAssistant(
        knowledge_base,
        OpenAIResponsesGenerator(
            model=model,
            reasoning_effort=reasoning_effort,
        ),
    )

    answer = assistant.answer("Which checks run before a pull request is merged?")

    record_property("model", model)
    record_property("reasoning_effort", reasoning_effort.value)
    record_property("answer", answer.text)

    assert answer.is_supported
    assert answer.citations[0].source == "quality-guide.md"
    assert "[1]" in answer.text
    assert "ruff" in answer.text.lower()
    assert "coverage" in answer.text.lower()
