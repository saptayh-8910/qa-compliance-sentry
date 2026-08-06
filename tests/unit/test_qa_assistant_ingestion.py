from pathlib import Path

import pytest

from qa_assistant.ingestion import chunk_documents, discover_documents, load_documents
from qa_assistant.models import SourceDocument


def test_discover_documents_recurses_deduplicates_and_sorts(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    markdown = tmp_path / "guide.md"
    text = nested / "notes.txt"
    markdown.write_text("# Guide\nUseful text", encoding="utf-8")
    text.write_text("Notes", encoding="utf-8")
    (nested / "ignored.json").write_text("{}", encoding="utf-8")

    discovered = discover_documents([nested, markdown, markdown])

    assert discovered == (markdown.resolve(), text.resolve())


def test_load_documents_uses_relative_citation_paths(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    guide = docs / "guide.md"
    guide.write_text("# Guide\nRetrieval guidance", encoding="utf-8")

    documents = load_documents([docs], base_dir=tmp_path)

    assert documents == (
        SourceDocument(source="docs/guide.md", text="# Guide\nRetrieval guidance"),
    )


def test_discover_documents_rejects_missing_and_unsupported_sources(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        discover_documents([tmp_path / "missing"])

    unsupported = tmp_path / "data.json"
    unsupported.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported document type"):
        discover_documents([unsupported])


def test_discover_documents_rejects_directory_without_supported_files(
    tmp_path: Path,
) -> None:
    (tmp_path / "data.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="no supported"):
        discover_documents([tmp_path])


def test_chunk_documents_preserves_headings_and_character_limit() -> None:
    document = SourceDocument(
        source="docs/guide.md",
        text=(
            "# QA Guide\n\nShort introduction.\n\n"
            "## Continuous integration\n\n"
            + "quality coverage deterministic pipeline "
            * 12
        ),
    )

    chunks = chunk_documents([document], max_chars=100)

    assert chunks[0].heading == "QA Guide"
    assert all(len(chunk.text) <= 100 for chunk in chunks)
    assert {chunk.heading for chunk in chunks[1:]} == {"Continuous integration"}
    assert [chunk.position for chunk in chunks] == list(range(len(chunks)))


def test_chunk_documents_does_not_treat_fenced_comments_as_headings() -> None:
    document = SourceDocument(
        source="docs/example.md",
        text=(
            "# Real heading\n\n```python\n~~~ literal text\n# code comment\n"
            "assert True\n```\n\n## Later heading\n\nMore guidance."
        ),
    )

    chunks = chunk_documents([document])

    assert len(chunks) == 2
    assert chunks[0].heading == "Real heading"
    assert "# code comment" in chunks[0].text
    assert chunks[1].heading == "Later heading"


def test_chunk_documents_supports_plain_text_and_skips_blank_documents() -> None:
    chunks = chunk_documents(
        [
            SourceDocument(source="notes.txt", text="plain QA notes"),
            SourceDocument(source="blank.md", text="  \n"),
        ]
    )

    assert len(chunks) == 1
    assert chunks[0].heading == "notes"
    assert chunks[0].text == "plain QA notes"


def test_chunk_documents_preserves_lines_in_long_markdown_tables() -> None:
    document = SourceDocument(
        source="docs/history.md",
        text=(
            "# Milestones\n\n| Version | Evidence |\n|---|---|\n"
            + "\n".join(f"| 0.{number} | {number * 10} tests |" for number in range(8))
        ),
    )

    chunks = chunk_documents([document], max_chars=100)

    assert len(chunks) > 1
    assert all("\n" in chunk.text for chunk in chunks)
    assert all("|" in chunk.text for chunk in chunks)


def test_chunk_documents_rejects_tiny_chunk_limit() -> None:
    with pytest.raises(ValueError, match="at least 100"):
        chunk_documents([], max_chars=99)
