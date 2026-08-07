from __future__ import annotations

import os
from collections.abc import Callable
from time import perf_counter

import pytest

from qa_assistant.evaluation import (
    EvaluationCase,
    evaluate_case,
    grounding_evaluation_cases,
)
from qa_assistant.openai_generator import OpenAIResponsesGenerator, ReasoningEffort

pytestmark = [pytest.mark.api, pytest.mark.external, pytest.mark.ai]


@pytest.mark.skipif(
    os.getenv("RUN_OPENAI_LIVE_TESTS") != "1",
    reason="set RUN_OPENAI_LIVE_TESTS=1 to allow six paid OpenAI API calls",
)
@pytest.mark.parametrize(
    ("model", "reasoning_effort"),
    [
        pytest.param("gpt-5.6-sol", ReasoningEffort.MEDIUM, id="sol-medium"),
        pytest.param("gpt-5.6-luna", ReasoningEffort.HIGH, id="luna-high"),
    ],
)
@pytest.mark.parametrize(
    "case",
    grounding_evaluation_cases(),
    ids=lambda case: case.identifier,
)
def test_openai_grounding_evaluation_live(
    model: str,
    reasoning_effort: ReasoningEffort,
    case: EvaluationCase,
    record_property: Callable[[str, object], None],
) -> None:
    generator = OpenAIResponsesGenerator(
        model=model,
        reasoning_effort=reasoning_effort,
    )
    started = perf_counter()

    result = evaluate_case(case, generator)
    duration = perf_counter() - started

    record_property("model", model)
    record_property("reasoning_effort", reasoning_effort.value)
    record_property("evaluation_case", case.identifier)
    record_property("passed", result.passed)
    record_property("duration_seconds", round(duration, 6))
    record_property("context_precision", result.metrics.context_precision)
    record_property("context_recall", result.metrics.context_recall)
    if result.metrics.hit_at_k is not None:
        record_property("hit_at_k", result.metrics.hit_at_k)
    if result.metrics.reciprocal_rank is not None:
        record_property("reciprocal_rank", result.metrics.reciprocal_rank)
    if result.metrics.citation_precision is not None:
        record_property("citation_precision", result.metrics.citation_precision)
    if result.metrics.citation_recall is not None:
        record_property("citation_recall", result.metrics.citation_recall)
    if result.answer is not None:
        record_property("answer", result.answer.text)
    if generator.last_usage is not None:
        record_property("input_tokens", generator.last_usage.input_tokens)
        record_property("output_tokens", generator.last_usage.output_tokens)
        record_property("total_tokens", generator.last_usage.total_tokens)
        record_property("reasoning_tokens", generator.last_usage.reasoning_tokens or 0)

    assert result.passed, result.failure_summary
