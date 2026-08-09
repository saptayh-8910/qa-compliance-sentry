from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from qa_assistant.evaluation import evaluate_case, grounding_evaluation_cases
from qa_assistant.generation import INSUFFICIENT_EVIDENCE
from qa_assistant.models import GenerationRequest
from qa_assistant.openai_generator import ResponseUsage
from qa_assistant.reporting import (
    DETERMINISTIC_GRADER,
    EVALUATION_REPORT_SCHEMA_VERSION,
    EvaluationObservation,
    EvaluationReport,
    EvaluationRunMetadata,
    evaluation_report_data,
    write_evaluation_report,
)


@dataclass
class ScriptedGenerator:
    responses: dict[str, str]

    def generate(self, request: GenerationRequest) -> str:
        return self.responses[request.question]


def _passing_observations() -> tuple[EvaluationObservation, ...]:
    cases = grounding_evaluation_cases()
    generator = ScriptedGenerator(
        {
            cases[0].question: "Ruff and coverage run before merge [1].",
            cases[2].question: INSUFFICIENT_EVIDENCE,
            cases[3].question: "Ruff and coverage run before merge [1].",
        }
    )
    results = tuple(evaluate_case(case, generator) for case in cases)
    return tuple(
        EvaluationObservation(
            result=result,
            duration_seconds=round((index + 1) / 10, 1),
            usage=(ResponseUsage(10, 5, 15, 2) if index == 0 else None),
        )
        for index, result in enumerate(results)
    )


def _report() -> EvaluationReport:
    return EvaluationReport(
        metadata=EvaluationRunMetadata(
            run_id="run-001",
            created_at=datetime(
                2026,
                8,
                9,
                23,
                30,
                tzinfo=timezone(timedelta(hours=9)),
            ),
            provider="scripted",
            model="reference-generator",
            reasoning_effort="none",
        ),
        observations=_passing_observations(),
    )


def test_report_serializes_summary_cases_null_metrics_and_telemetry() -> None:
    data = evaluation_report_data(_report())

    assert data["schema_version"] == EVALUATION_REPORT_SCHEMA_VERSION == "1.0"
    assert data["run"] == {
        "run_id": "run-001",
        "created_at": "2026-08-09T14:30:00.000000Z",
        "dataset": "stage3-grounding-v1",
        "grader": DETERMINISTIC_GRADER,
        "provider": "scripted",
        "model": "reference-generator",
        "reasoning_effort": "none",
    }
    assert data["summary"]["case_count"] == 4
    assert data["summary"]["passed_count"] == 4
    assert data["summary"]["pass_rate"] == 1.0

    supported = data["cases"][0]
    assert supported["answer"]["citations"] == [
        {
            "identifier": 1,
            "source": "quality-guide.md",
            "heading": "Merge checks",
        }
    ]
    assert supported["telemetry"] == {
        "duration_seconds": 0.1,
        "usage": {
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
            "reasoning_tokens": 2,
        },
    }

    unsupported = data["cases"][1]
    assert unsupported["answer"]["citations"] == []
    assert unsupported["metrics"]["hit_at_k"] is None
    assert unsupported["metrics"]["reciprocal_rank"] is None
    assert unsupported["metrics"]["citation_precision"] is None
    assert unsupported["metrics"]["citation_recall"] is None
    assert unsupported["telemetry"]["usage"] is None


def test_report_writer_creates_parent_and_replaces_existing_file(
    tmp_path: Path,
) -> None:
    output = tmp_path / "nested" / "evaluation.json"
    output.parent.mkdir()
    output.write_text("stale", encoding="utf-8")

    write_evaluation_report(_report(), output)

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data == evaluation_report_data(_report())
    assert output.read_text(encoding="utf-8").endswith("\n")
    assert tuple(output.parent.glob("*.tmp")) == ()


def test_report_writer_removes_temporary_file_when_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "evaluation.json"

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError(f"cannot replace {destination} from {source.name}")

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(OSError, match="cannot replace"):
        write_evaluation_report(_report(), output)

    assert not output.exists()
    assert tuple(tmp_path.iterdir()) == ()


def test_tracked_json_schema_matches_exporter_version() -> None:
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "schemas"
        / "evaluation-report-v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert schema["required"] == ["schema_version", "run", "summary", "cases"]
    assert schema["properties"]["cases"]["minItems"] == 1


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"run_id": " "}, "run_id cannot be empty"),
        ({"provider": " "}, "provider cannot be empty"),
        ({"dataset": " "}, "dataset cannot be empty"),
        ({"grader": " "}, "grader cannot be empty"),
        ({"created_at": datetime(2026, 8, 9)}, "must include a timezone"),
        ({"model": " "}, "model cannot be empty"),
        ({"reasoning_effort": " "}, "reasoning_effort cannot be empty"),
    ],
)
def test_report_metadata_rejects_invalid_values(
    kwargs: dict[str, object],
    message: str,
) -> None:
    values: dict[str, object] = {
        "run_id": "run",
        "created_at": datetime.now(UTC),
        "provider": "extractive",
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=message):
        EvaluationRunMetadata(**values)  # type: ignore[arg-type]


def test_report_rejects_empty_and_duplicate_observations() -> None:
    metadata = EvaluationRunMetadata("run", datetime.now(UTC), "scripted")
    observation = _passing_observations()[0]

    with pytest.raises(ValueError, match="at least one observation"):
        EvaluationReport(metadata, ())
    with pytest.raises(ValueError, match="identifiers must be unique"):
        EvaluationReport(metadata, (observation, observation))


@pytest.mark.parametrize(
    ("duration", "usage", "message"),
    [
        (-0.1, None, "duration cannot be negative"),
        (0.1, ResponseUsage(-1, 2, 1), "token counts cannot be negative"),
        (0.1, ResponseUsage(1, 2, 3, -1), "reasoning tokens cannot be negative"),
    ],
)
def test_observation_rejects_invalid_telemetry(
    duration: float,
    usage: ResponseUsage | None,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        EvaluationObservation(_passing_observations()[0].result, duration, usage)
