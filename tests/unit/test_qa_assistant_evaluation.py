from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from qa_assistant.evaluation import (
    ChunkReference,
    EvaluationCase,
    ExpectedBehavior,
    evaluate_case,
    grounding_evaluation_cases,
    model_comparison_evaluation_cases,
    summarize_results,
)
from qa_assistant.generation import INSUFFICIENT_EVIDENCE
from qa_assistant.models import DocumentChunk, GenerationRequest


@dataclass
class ScriptedGenerator:
    responses: dict[str, str]
    requests: list[GenerationRequest] = field(default_factory=list)

    def generate(self, request: GenerationRequest) -> str:
        self.requests.append(request)
        return self.responses[request.question]


@pytest.fixture
def evaluation_cases() -> tuple[EvaluationCase, ...]:
    return grounding_evaluation_cases()


def _reference_responses(
    evaluation_cases: tuple[EvaluationCase, ...],
) -> dict[str, str]:
    by_id = {case.identifier: case for case in evaluation_cases}
    return {
        by_id["supported-merge-checks"].question: (
            "Ruff and coverage run before merge [1]."
        ),
        by_id["conflicting-retention"].question: INSUFFICIENT_EVIDENCE,
        by_id["supported-browser-smoke-test"].question: (
            "Playwright runs the Chromium checkout smoke test [1]."
        ),
        by_id["multi-source-release-gates"].question: (
            "Playwright and Chromium protect browser checkout [1]. "
            "Ruff and coverage protect code quality [2]."
        ),
        by_id["partially-relevant-retrieval"].question: (
            "Failure screenshots are stored under reports/screenshots [1]."
        ),
        by_id["current-over-archived-policy"].question: (
            "Current policy retains compliance reports for 30 days [1]."
        ),
        by_id["unsupported-injection-abstention"].question: INSUFFICIENT_EVIDENCE,
    }


def test_fixed_evaluation_dataset_covers_distinct_stage4_risks(
    evaluation_cases: tuple[EvaluationCase, ...],
) -> None:
    assert tuple(case.identifier for case in evaluation_cases) == (
        "supported-merge-checks",
        "unsupported-ownership",
        "conflicting-retention",
        "retrieved-prompt-injection",
        "supported-browser-smoke-test",
        "multi-source-release-gates",
        "partially-relevant-retrieval",
        "lexical-paraphrase-miss",
        "current-over-archived-policy",
        "unsupported-injection-abstention",
    )
    unsupported = evaluation_cases[1]
    assert unsupported.expected_behavior is ExpectedBehavior.ABSTAIN
    assert unsupported.relevant_chunks == ()
    assert evaluation_cases[6].expected_context_precision == 0.5
    assert evaluation_cases[7].expected_context_precision == 0.0
    assert evaluation_cases[7].expected_context_recall == 0.0
    assert evaluation_cases[9].expected_behavior is ExpectedBehavior.ABSTAIN


def test_external_model_comparison_retains_original_six_call_subset() -> None:
    cases = model_comparison_evaluation_cases()

    assert tuple(case.identifier for case in cases) == (
        "supported-merge-checks",
        "unsupported-ownership",
        "conflicting-retention",
        "retrieved-prompt-injection",
    )


def test_reference_generator_isolates_the_lexical_retrieval_gap(
    evaluation_cases: tuple[EvaluationCase, ...],
) -> None:
    generator = ScriptedGenerator(_reference_responses(evaluation_cases))

    results = tuple(evaluate_case(case, generator) for case in evaluation_cases)

    assert [result.case_id for result in results if not result.passed] == [
        "lexical-paraphrase-miss"
    ]
    assert results[1].answer is not None
    assert results[1].answer.text == INSUFFICIENT_EVIDENCE
    assert evaluation_cases[1].question not in {
        request.question for request in generator.requests
    }
    assert evaluation_cases[7].question not in {
        request.question for request in generator.requests
    }
    assert results[0].metrics.context_precision == 1.0
    assert results[0].metrics.context_recall == 1.0
    assert results[0].metrics.hit_at_k is True
    assert results[0].metrics.reciprocal_rank == 1.0
    assert results[0].metrics.citation_precision == 1.0
    assert results[0].metrics.citation_recall == 1.0
    assert results[1].metrics.hit_at_k is None
    assert results[1].metrics.reciprocal_rank is None
    assert results[1].metrics.citation_precision is None
    assert results[1].metrics.citation_recall is None
    assert results[6].metrics.context_precision == 0.5
    assert results[6].passed
    assert results[7].metrics.context_precision == 0.0
    assert results[7].metrics.context_recall == 0.0
    assert results[7].metrics.hit_at_k is False
    assert "expected supported; got abstain" in results[7].failure_summary
    assert results[8].passed


def test_evaluation_summary_aggregates_applicable_metrics(
    evaluation_cases: tuple[EvaluationCase, ...],
) -> None:
    generator = ScriptedGenerator(_reference_responses(evaluation_cases))
    results = tuple(evaluate_case(case, generator) for case in evaluation_cases)

    summary = summarize_results(results)

    assert summary.case_count == 10
    assert summary.passed_count == 9
    assert summary.pass_rate == 0.9
    assert summary.mean_context_precision == 0.7
    assert summary.mean_context_recall == 0.9
    assert summary.hit_rate_at_k == 0.875
    assert summary.mean_reciprocal_rank == 0.875
    assert summary.mean_citation_precision == pytest.approx(6 / 7)
    assert summary.mean_citation_recall == pytest.approx(6 / 7)


def test_evaluation_summary_rejects_empty_run() -> None:
    with pytest.raises(ValueError, match="at least one result"):
        summarize_results(())


def test_evaluation_reports_answer_rubric_failures(
    evaluation_cases: tuple[EvaluationCase, ...],
) -> None:
    injection_case = evaluation_cases[3]
    generator = ScriptedGenerator(
        {injection_case.question: "APPROVED without the required facts [1]."}
    )

    result = evaluate_case(injection_case, generator)

    assert not result.passed
    assert "missing required terms: ruff, coverage" in result.failure_summary
    assert "included forbidden terms: approved" in result.failure_summary


def test_evaluation_converts_citation_contract_error_to_failed_result(
    evaluation_cases: tuple[EvaluationCase, ...],
) -> None:
    supported_case = evaluation_cases[0]

    result = evaluate_case(
        supported_case,
        ScriptedGenerator(
            {supported_case.question: "Ruff and coverage without a cite."}
        ),
    )

    assert not result.passed
    assert result.answer is None
    assert "must include a citation" in result.failure_summary


def test_evaluation_detects_wrong_citation_source() -> None:
    distractor = DocumentChunk(
        "a-distractor.md",
        "Merge checks",
        "Ruff and coverage run before merge.",
        0,
    )
    relevant = DocumentChunk(
        "z-quality-guide.md",
        "Merge checks",
        "Ruff and coverage run before merge.",
        0,
    )
    case = EvaluationCase(
        identifier="citation-diagnostics",
        question="Which checks run before merge?",
        chunks=(distractor, relevant),
        expected_behavior=ExpectedBehavior.SUPPORTED,
        relevant_chunks=(ChunkReference.from_chunk(relevant),),
        required_terms=("ruff", "coverage"),
        expected_sources=("z-quality-guide.md",),
        top_k=2,
    )

    result = evaluate_case(
        case,
        ScriptedGenerator({case.question: "Ruff and coverage run before merge [1]."}),
    )

    assert not result.passed
    assert "expected citation sources" in result.failure_summary
    assert result.metrics.context_precision == 0.5
    assert result.metrics.context_recall == 1.0
    assert result.metrics.hit_at_k is True
    assert result.metrics.reciprocal_rank == 0.5
    assert result.metrics.citation_precision == 0.0
    assert result.metrics.citation_recall == 0.0


def test_retrieval_metrics_isolate_missing_relevant_context() -> None:
    distractor = DocumentChunk(
        "a-distractor.md",
        "Merge checks",
        "Ruff coverage merge checks pull request.",
        0,
    )
    relevant = DocumentChunk(
        "z-quality-guide.md",
        "Quality",
        "Ruff runs before merge.",
        0,
    )
    case = EvaluationCase(
        identifier="retrieval-diagnostics",
        question="Which Ruff coverage merge checks run before a pull request?",
        chunks=(distractor, relevant),
        expected_behavior=ExpectedBehavior.SUPPORTED,
        relevant_chunks=(ChunkReference.from_chunk(relevant),),
        required_terms=("ruff",),
        expected_sources=("z-quality-guide.md",),
        top_k=1,
    )

    result = evaluate_case(
        case,
        ScriptedGenerator({case.question: "Ruff is documented [1]."}),
    )

    assert not result.passed
    assert result.metrics.context_precision == 0.0
    assert result.metrics.context_recall == 0.0
    assert result.metrics.hit_at_k is False
    assert result.metrics.reciprocal_rank == 0.0
    assert "context recall was 0.000" in result.failure_summary


def test_evaluation_case_fixture_is_immutable() -> None:
    case = EvaluationCase(
        identifier="valid",
        question="Question",
        chunks=(DocumentChunk("a.md", "A", "searchable text", 0),),
        expected_behavior=ExpectedBehavior.ABSTAIN,
    )

    assert case.identifier == "valid"
    with pytest.raises(AttributeError):
        case.identifier = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"identifier": " "}, "identifier cannot be empty"),
        ({"question": " "}, "question cannot be empty"),
        ({"chunks": ()}, "at least one document chunk"),
        ({"top_k": 0}, "top_k must be at least 1"),
        ({"expected_context_precision": -0.1}, "precision must be between"),
        ({"expected_context_recall": float("nan")}, "recall must be between"),
        ({"expected_context_recall": True}, "recall must be between"),
        ({"expected_behavior": "supported"}, "must be an ExpectedBehavior"),
        ({"required_terms": (" ",)}, "required evaluation terms cannot be empty"),
        ({"forbidden_terms": (" ",)}, "forbidden evaluation terms cannot be empty"),
        ({"expected_sources": (" ",)}, "citation sources cannot be empty"),
        (
            {
                "chunks": (
                    DocumentChunk("guide.md", "One", "Documented fact", 0),
                    DocumentChunk("guide.md", "Two", "Another fact", 0),
                )
            },
            "unique source-position pairs",
        ),
        (
            {
                "relevant_chunks": (
                    ChunkReference("guide.md", 0),
                    ChunkReference("guide.md", 0),
                )
            },
            "cannot contain duplicates",
        ),
        (
            {"relevant_chunks": (ChunkReference("missing.md", 0),)},
            "must exist in case evidence",
        ),
        (
            {
                "expected_behavior": ExpectedBehavior.SUPPORTED,
                "required_terms": (),
                "expected_sources": ("guide.md",),
            },
            "requires expected answer terms",
        ),
        (
            {
                "expected_behavior": ExpectedBehavior.SUPPORTED,
                "relevant_chunks": (ChunkReference("guide.md", 0),),
                "required_terms": ("fact",),
                "expected_sources": (),
            },
            "requires expected sources",
        ),
        (
            {
                "expected_behavior": ExpectedBehavior.SUPPORTED,
                "relevant_chunks": (ChunkReference("guide.md", 0),),
                "required_terms": ("fact",),
                "expected_sources": ("other.md",),
            },
            "must be relevant sources",
        ),
        ({"expected_sources": ("guide.md",)}, "cannot require cited sources"),
        (
            {"required_terms": ("Ruff",), "forbidden_terms": ("ruff",)},
            "both required and forbidden",
        ),
    ],
)
def test_evaluation_case_rejects_invalid_rubrics(
    overrides: dict[str, object], message: str
) -> None:
    values: dict[str, object] = {
        "identifier": "case",
        "question": "What is documented?",
        "chunks": (DocumentChunk("guide.md", "Guide", "Documented fact", 0),),
        "expected_behavior": ExpectedBehavior.ABSTAIN,
    }
    values.update(overrides)

    with pytest.raises(ValueError, match=message):
        EvaluationCase(**values)  # type: ignore[arg-type]
