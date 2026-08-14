import json
from pathlib import Path

import pytest

import qa_assistant.workspace as workspace
from qa_assistant.workspace import (
    WorkspaceDataError,
    build_session,
    evaluate_question,
    load_catalog,
    load_library_documents,
    uploaded_documents,
)

STARTER_CASES = load_catalog()["starter_cases"]


def test_pinned_asvs_library_checksum_and_requirement_sections() -> None:
    catalog = load_catalog()

    assert catalog["entries"][0]["version"] == "5.0.0"
    documents = load_library_documents(["owasp-asvs-5.0.0"])
    session = build_session({"library_ids": ["owasp-asvs-5.0.0"], "files": []})

    assert len(documents) == 1
    assert session.assistant.knowledge_base.document_count == 1
    assert len(session.assistant.knowledge_base.chunks) == 345


@pytest.mark.parametrize(
    "case",
    STARTER_CASES,
    ids=[case["id"] for case in STARTER_CASES],
)
def test_starter_questions_report_plain_english_labelled_metrics(
    case: dict[str, object],
) -> None:
    session = build_session({"library_ids": ["owasp-asvs-5.0.0"], "files": []})

    result = evaluate_question(
        session,
        question=str(case["question"]),
        expected_ids=case["expected_evidence"],
        top_k=3,
    )

    metrics = {item["name"]: item for item in result["metrics"]}
    assert metrics["Hit@K"]["display"] == "Hit"
    assert metrics["Context recall"]["display"] == "100%"
    assert metrics["Reciprocal rank"]["display"] == "1.00"
    assert metrics["Citation recall"]["display"] == "100%"
    assert "This result" not in metrics["Hit@K"]["meaning"]
    assert result["citations"]
    assert result["results"][0]["evidence_ids"]


def test_unlabelled_question_marks_accuracy_as_not_measured() -> None:
    session = build_session(
        {
            "library_ids": [],
            "files": [{"name": "guide.md", "text": "# CI\n\nCoverage blocks merges."}],
        }
    )

    result = evaluate_question(
        session,
        question="What blocks merges?",
        expected_ids=[],
        top_k=1,
    )

    assert all(metric["display"] == "Not measured" for metric in result["metrics"][:-1])
    assert result["metrics"][-1]["name"] == "Local response time"


def test_uploads_stay_in_memory_and_validate_names_and_formats() -> None:
    documents = uploaded_documents(
        [{"name": "policy.txt", "text": "Retain logs for thirty days."}]
    )

    assert documents[0].source == "uploads/policy.txt"
    assert documents[0].text == "Retain logs for thirty days."
    with pytest.raises(WorkspaceDataError, match="unsafe"):
        uploaded_documents([{"name": "../secret.txt", "text": "no"}])
    with pytest.raises(WorkspaceDataError, match="unsupported"):
        uploaded_documents([{"name": "sheet.csv", "text": "no"}])


def test_library_checksum_tampering_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.json"
    source.write_text("{}", encoding="utf-8")
    catalog = tmp_path / "catalog.json"
    catalog.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "id": "test",
                        "path": "source.json",
                        "sha256": "incorrect",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    cases = tmp_path / "cases.json"
    cases.write_text('{"cases": []}', encoding="utf-8")
    monkeypatch.setattr(workspace, "LIBRARY_ROOT", tmp_path)
    monkeypatch.setattr(workspace, "CATALOG_PATH", catalog)
    monkeypatch.setattr(workspace, "STARTER_CASES_PATH", cases)

    with pytest.raises(WorkspaceDataError, match="checksum mismatch"):
        load_library_documents(["test"])


def test_workspace_html_has_upload_and_plain_english_criteria() -> None:
    html = workspace.WORKSPACE_HTML.read_text(encoding="utf-8")

    assert 'id="files"' in html
    assert "Expected evidence IDs" in html
    assert "Evaluation criteria and result" in html
    assert "Not measured" in html
