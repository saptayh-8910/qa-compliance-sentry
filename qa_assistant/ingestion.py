"""Discover UTF-8 documents and split them into heading-aware chunks."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Sequence
from pathlib import Path

from qa_assistant.models import DocumentChunk, SourceDocument

SUPPORTED_SUFFIXES = frozenset({".json", ".md", ".txt"})
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")


def discover_documents(sources: Iterable[Path]) -> tuple[Path, ...]:
    """Return unique supported files from explicit files and directories."""
    discovered: dict[Path, Path] = {}
    for source in sources:
        if not source.exists():
            raise FileNotFoundError(f"document source does not exist: {source}")
        if source.is_file():
            if source.suffix.lower() not in SUPPORTED_SUFFIXES:
                raise ValueError(f"unsupported document type: {source}")
            discovered.setdefault(source.resolve(), source.resolve())
            continue
        if not source.is_dir():
            raise ValueError(f"document source is not a file or directory: {source}")
        for candidate in source.rglob("*"):
            if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES:
                discovered.setdefault(candidate.resolve(), candidate.resolve())

    if not discovered:
        raise ValueError("no supported .md or .txt documents were found")
    return tuple(sorted(discovered.values(), key=lambda path: path.as_posix()))


def load_documents(
    sources: Iterable[Path], *, base_dir: Path | None = None
) -> tuple[SourceDocument, ...]:
    """Load discovered sources and make in-repository citations relative."""
    base = (base_dir or Path.cwd()).resolve()
    documents: list[SourceDocument] = []
    for path in discover_documents(sources):
        try:
            display_path = path.relative_to(base).as_posix()
        except ValueError:
            display_path = path.as_posix()
        documents.append(
            document_from_text(display_path, path.read_text(encoding="utf-8"))
        )
    return tuple(documents)


def document_from_text(source: str, text: str) -> SourceDocument:
    """Create a searchable document, adapting supported structured sources."""
    suffix = Path(source).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"unsupported document type: {source}")
    if suffix == ".json":
        text = _asvs_json_to_markdown(text, source=source)
    return SourceDocument(source=source, text=text)


def _asvs_json_to_markdown(text: str, *, source: str) -> str:
    """Convert the official OWASP ASVS JSON structure into cited requirements."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON document: {source}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"unsupported JSON document structure: {source}")

    version = data.get("Version")
    chapters = data.get("Requirements")
    if data.get("ShortName") != "ASVS" or not isinstance(version, str):
        raise ValueError(
            f"unsupported JSON document: {source}; only official OWASP ASVS JSON "
            "is currently accepted"
        )
    if not isinstance(chapters, list):
        raise ValueError(f"invalid OWASP ASVS requirements: {source}")

    sections: list[str] = []
    for chapter in chapters:
        if not isinstance(chapter, dict):
            raise ValueError(f"invalid OWASP ASVS chapter: {source}")
        chapter_name = chapter.get("Name")
        chapter_sections = chapter.get("Items")
        if not isinstance(chapter_name, str) or not isinstance(chapter_sections, list):
            raise ValueError(f"invalid OWASP ASVS chapter: {source}")
        for section in chapter_sections:
            if not isinstance(section, dict):
                raise ValueError(f"invalid OWASP ASVS section: {source}")
            section_name = section.get("Name")
            requirements = section.get("Items")
            if not isinstance(section_name, str) or not isinstance(requirements, list):
                raise ValueError(f"invalid OWASP ASVS section: {source}")
            for requirement in requirements:
                if not isinstance(requirement, dict):
                    raise ValueError(f"invalid OWASP ASVS requirement: {source}")
                shortcode = requirement.get("Shortcode")
                description = requirement.get("Description")
                level = requirement.get("L")
                if not all(
                    isinstance(value, str) for value in (shortcode, description, level)
                ):
                    raise ValueError(f"invalid OWASP ASVS requirement: {source}")
                number = shortcode.removeprefix("V")
                identifier = f"v{version}-{number}"
                sections.append(
                    f"## {identifier} — {chapter_name} > {section_name}\n\n"
                    f"Requirement ID: {identifier}\n\n"
                    f"ASVS shortcode: {shortcode}\n\n"
                    f"Verification level: L{level}\n\n"
                    f"Requirement: {description.strip()}"
                )

    if not sections:
        raise ValueError(f"OWASP ASVS document contains no requirements: {source}")
    return "\n\n".join(sections)


def _markdown_sections(document: SourceDocument) -> list[tuple[str, str]]:
    default_heading = Path(document.source).stem.replace("_", " ").strip() or "Document"
    heading = default_heading
    lines: list[str] = []
    sections: list[tuple[str, str]] = []
    fence_marker: str | None = None

    def flush() -> None:
        body = "\n".join(lines).strip()
        if body:
            sections.append((heading, body))

    for line in document.text.splitlines():
        fence = _FENCE.match(line)
        if fence:
            marker = fence.group(1)
            if fence_marker is None:
                fence_marker = marker
            elif fence_marker == marker:
                fence_marker = None
            lines.append(line)
            continue
        match = None if fence_marker else _HEADING.match(line)
        if match:
            flush()
            heading = match.group(2).strip()
            lines = []
        else:
            lines.append(line)
    flush()
    return sections


def _split_long_line(line: str, max_chars: int) -> list[str]:
    words = line.split()
    pieces: list[str] = []
    current = ""
    for word in words:
        while len(word) > max_chars:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(word[:max_chars])
            word = word[max_chars:]
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            pieces.append(current)
            current = word
    if current:
        pieces.append(current)
    return pieces


def _split_long_text(text: str, max_chars: int) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        lines.extend(
            [line] if len(line) <= max_chars else _split_long_line(line, max_chars)
        )

    pieces: list[str] = []
    current = ""
    for line in lines:
        candidate = line if not current else f"{current}\n{line}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            pieces.append(current)
            current = line
    if current:
        pieces.append(current)
    return pieces


def _split_section(text: str, max_chars: int) -> list[str]:
    paragraphs = [
        "\n".join(line.rstrip() for line in paragraph.splitlines()).strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]
    pieces: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidates = (
            [paragraph]
            if len(paragraph) <= max_chars
            else _split_long_text(paragraph, max_chars)
        )
        for candidate_part in candidates:
            candidate = (
                candidate_part if not current else f"{current}\n\n{candidate_part}"
            )
            if len(candidate) <= max_chars:
                current = candidate
            else:
                pieces.append(current)
                current = candidate_part
    if current:
        pieces.append(current)
    return pieces


def chunk_documents(
    documents: Sequence[SourceDocument], *, max_chars: int = 1_200
) -> tuple[DocumentChunk, ...]:
    """Split documents at headings and paragraph boundaries."""
    if max_chars < 100:
        raise ValueError("max_chars must be at least 100")

    chunks: list[DocumentChunk] = []
    for document in documents:
        sections = (
            _markdown_sections(document)
            if Path(document.source).suffix.lower() in {".json", ".md"}
            else [(Path(document.source).stem, document.text.strip())]
        )
        position = 0
        for heading, section_text in sections:
            for text in _split_section(section_text, max_chars):
                chunks.append(
                    DocumentChunk(
                        source=document.source,
                        heading=heading,
                        text=text,
                        position=position,
                    )
                )
                position += 1
    return tuple(chunks)
