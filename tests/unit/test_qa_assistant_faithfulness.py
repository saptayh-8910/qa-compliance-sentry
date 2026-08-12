from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from qa_assistant.faithfulness import (
    DeterministicFaithfulnessJudge,
    FaithfulnessExample,
    FaithfulnessLabel,
    JudgeValidationPolicy,
    faithfulness_examples,
    validate_faithfulness_judge,
)
from qa_assistant.faithfulness_reporting import (
    FAITHFULNESS_REPORT_SCHEMA_VERSION,
    faithfulness_report_data,
    write_faithfulness_report,
)


def test_human_labelled_dataset_is_balanced_and_explainable() -> None:
    examples = faithfulness_examples()

    assert len(examples) == 15
    assert len({example.identifier for example in examples}) == 15
    assert {
        label: sum(example.human_label is label for example in examples)
        for label in FaithfulnessLabel
    } == {
        FaithfulnessLabel.SUPPORTED: 5,
        FaithfulnessLabel.CONTRADICTED: 5,
        FaithfulnessLabel.UNSUPPORTED: 5,
    }
    assert all(example.explanation for example in examples)


def test_deterministic_candidate_is_validated_against_human_labels() -> None:
    validation = validate_faithfulness_judge(DeterministicFaithfulnessJudge())
    metrics = validation.metrics

    assert validation.validated is True
    assert metrics.example_count == 15
    assert metrics.human_supported_count == 5
    assert metrics.human_faithfulness_rate == pytest.approx(1 / 3)
    assert metrics.exact_match_count == 15
    assert metrics.accuracy == 1.0
    assert metrics.unfaithful_precision == 1.0
    assert metrics.unfaithful_recall == 1.0
    assert metrics.unfaithful_f1 == 1.0
    assert metrics.false_positive_count == 0
    assert metrics.false_negative_count == 0
    assert metrics.confusion_matrix == {
        "supported": {"supported": 5, "contradicted": 0, "unsupported": 0},
        "contradicted": {"supported": 0, "contradicted": 5, "unsupported": 0},
        "unsupported": {"supported": 0, "contradicted": 0, "unsupported": 5},
    }


def test_validation_rejects_judge_with_dangerous_false_negatives() -> None:
    class AlwaysSupportedJudge:
        name = "unsafe-always-supported"

        def classify(self, example: FaithfulnessExample) -> FaithfulnessLabel:
            return FaithfulnessLabel.SUPPORTED

    validation = validate_faithfulness_judge(AlwaysSupportedJudge())

    assert validation.validated is False
    assert validation.metrics.accuracy == pytest.approx(1 / 3)
    assert validation.metrics.unfaithful_recall == 0.0
    assert validation.metrics.false_negative_count == 10


def test_validation_rejects_false_positive_only_candidate_under_accuracy_gate() -> None:
    class OverBlockingJudge:
        name = "over-blocking"

        def classify(self, example: FaithfulnessExample) -> FaithfulnessLabel:
            return (
                FaithfulnessLabel.UNSUPPORTED
                if example.human_label is FaithfulnessLabel.SUPPORTED
                else example.human_label
            )

    validation = validate_faithfulness_judge(OverBlockingJudge())

    assert validation.metrics.false_positive_count == 5
    assert validation.metrics.false_negative_count == 0
    assert validation.metrics.unfaithful_recall == 1.0
    assert validation.metrics.accuracy == pytest.approx(2 / 3)
    assert validation.validated is False


def test_validation_rejects_empty_or_duplicate_human_labels() -> None:
    judge = DeterministicFaithfulnessJudge()
    duplicate = faithfulness_examples()[0]

    with pytest.raises(ValueError, match="at least one example"):
        validate_faithfulness_judge(judge, ())
    with pytest.raises(ValueError, match="identifiers must be unique"):
        validate_faithfulness_judge(judge, (duplicate, duplicate))


def test_validation_rejects_invalid_judge_identity_or_label() -> None:
    class InvalidJudge:
        name = "invalid-label"

        def classify(self, example: FaithfulnessExample) -> object:
            return "supported"

    class AnonymousJudge(InvalidJudge):
        name = " "

    with pytest.raises(ValueError, match="must return a FaithfulnessLabel"):
        validate_faithfulness_judge(InvalidJudge())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="judge name cannot be empty"):
        validate_faithfulness_judge(AnonymousJudge())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="dataset_name cannot be empty"):
        validate_faithfulness_judge(DeterministicFaithfulnessJudge(), dataset_name=" ")


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"minimum_accuracy": -0.1}, "between 0 and 1"),
        ({"minimum_unfaithful_recall": float("nan")}, "between 0 and 1"),
        ({"maximum_false_negatives": -1}, "non-negative integer"),
        ({"maximum_false_negatives": True}, "non-negative integer"),
    ],
)
def test_validation_policy_rejects_invalid_thresholds(
    kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        JudgeValidationPolicy(**kwargs)  # type: ignore[arg-type]


def test_report_serializes_human_labels_policy_and_decisions() -> None:
    validation = validate_faithfulness_judge(DeterministicFaithfulnessJudge())
    data = faithfulness_report_data(
        validation,
        run_id="faithfulness-001",
        created_at=datetime(2026, 8, 12, 23, tzinfo=UTC),
    )

    assert data["schema_version"] == FAITHFULNESS_REPORT_SCHEMA_VERSION == "1.0"
    assert data["run"] == {
        "run_id": "faithfulness-001",
        "created_at": "2026-08-12T23:00:00.000000Z",
        "dataset": "stage4-human-claims-v1",
        "judge": "deterministic-claim-baseline-v1",
        "label_source": "human-authored-version-controlled",
    }
    assert data["summary"]["validated"] is True
    assert data["summary"]["accuracy"] == 1.0
    assert data["policy"] == {
        "minimum_accuracy": 0.9,
        "minimum_unfaithful_recall": 0.95,
        "maximum_false_negatives": 0,
    }
    assert data["claims"][1]["human_label"] == "contradicted"
    assert data["claims"][1]["judge_label"] == "contradicted"
    assert data["claims"][1]["correct"] is True


def test_report_writer_is_atomic_and_schema_is_tracked(tmp_path: Path) -> None:
    data = faithfulness_report_data(
        validate_faithfulness_judge(DeterministicFaithfulnessJudge()),
        run_id="run",
        created_at=datetime.now(UTC),
    )
    output = tmp_path / "nested" / "faithfulness.json"
    write_faithfulness_report(data, output)

    assert json.loads(output.read_text(encoding="utf-8")) == data
    assert output.read_text(encoding="utf-8").endswith("\n")
    assert tuple(output.parent.glob("*.tmp")) == ()
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "schemas"
        / "faithfulness-report-v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == "1.0"


def test_report_requires_run_identity_and_timezone() -> None:
    validation = validate_faithfulness_judge(DeterministicFaithfulnessJudge())
    with pytest.raises(ValueError, match="run_id"):
        faithfulness_report_data(validation, run_id=" ", created_at=datetime.now(UTC))
    with pytest.raises(ValueError, match="timezone"):
        faithfulness_report_data(
            validation, run_id="run", created_at=datetime(2026, 8, 12)
        )
