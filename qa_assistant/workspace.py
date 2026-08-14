"""Local browser workspace for uploaded and version-pinned document testing."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import webbrowser
from collections import OrderedDict
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from dotenv import load_dotenv

from qa_assistant.assistant import QAAssistant
from qa_assistant.generation import (
    EXTRACTIVE_PREFIX,
    AnswerGenerator,
    ExtractiveGenerator,
)
from qa_assistant.ingestion import (
    SUPPORTED_SUFFIXES,
    document_from_text,
    load_documents,
)
from qa_assistant.models import (
    GenerationUsage,
    GroundedAnswer,
    SearchResult,
    SourceDocument,
)
from qa_assistant.ollama_generator import (
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_MODEL,
    OllamaAdapterError,
    OllamaGenerator,
)
from qa_assistant.openai_generator import (
    DEFAULT_OPENAI_MODEL,
    DEFAULT_REASONING_EFFORT,
    OpenAIAdapterError,
    OpenAIResponsesGenerator,
)
from qa_assistant.service import QAKnowledgeBase

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LIBRARY_ROOT = PROJECT_ROOT / "data" / "library"
CATALOG_PATH = LIBRARY_ROOT / "catalog.json"
STARTER_CASES_PATH = LIBRARY_ROOT / "owasp-asvs-5.0.0" / "starter_cases.json"
WORKSPACE_HTML = Path(__file__).with_name("workspace.html")
MAX_REQUEST_BYTES = 6_000_000
MAX_UPLOAD_FILES = 20
MAX_UPLOAD_CHARS = 5_000_000
MAX_SESSIONS = 10
_EVIDENCE_ID = re.compile(r"v\d+\.\d+\.\d+-\d+\.\d+\.\d+", re.IGNORECASE)
EVIDENCE_MODE = "evidence"
LOCAL_AI_MODE = "local_ai"
PLAIN_ENGLISH_MODE = "plain_english"


class WorkspaceDataError(ValueError):
    """Raised when workspace input or pinned library data is invalid."""


@dataclass(slots=True)
class WorkspaceSession:
    """One bounded in-memory browser indexing session."""

    assistant: QAAssistant
    sources: tuple[str, ...]


class WorkspaceStore:
    """Keep recent local sessions without writing uploaded documents to disk."""

    def __init__(self, *, capacity: int = MAX_SESSIONS) -> None:
        self.capacity = capacity
        self._sessions: OrderedDict[str, WorkspaceSession] = OrderedDict()

    def put(self, session: WorkspaceSession) -> str:
        identifier = str(uuid4())
        self._sessions[identifier] = session
        while len(self._sessions) > self.capacity:
            self._sessions.popitem(last=False)
        return identifier

    def get(self, identifier: str) -> WorkspaceSession:
        try:
            session = self._sessions.pop(identifier)
        except KeyError as exc:
            raise WorkspaceDataError(
                "This document session expired. Index the documents again."
            ) from exc
        self._sessions[identifier] = session
        return session


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WorkspaceDataError(f"unable to read workspace data: {path}") from exc
    if not isinstance(data, dict):
        raise WorkspaceDataError(f"workspace data must be a JSON object: {path}")
    return data


def load_catalog() -> dict[str, Any]:
    """Load the public library catalog and starter evaluation cases."""
    catalog = _read_json_object(CATALOG_PATH)
    cases = _read_json_object(STARTER_CASES_PATH)
    entries = catalog.get("entries")
    starter_cases = cases.get("cases")
    if not isinstance(entries, list) or not isinstance(starter_cases, list):
        raise WorkspaceDataError("library catalog is missing entries or starter cases")
    load_dotenv()
    return {
        "entries": entries,
        "starter_cases": starter_cases,
        "answer_modes": {
            EVIDENCE_MODE: {
                "available": True,
                "label": "Direct evidence — free",
            },
            LOCAL_AI_MODE: {
                "available": shutil.which("ollama") is not None,
                "label": "Local AI — no API fee",
                "model": os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
            },
            PLAIN_ENGLISH_MODE: {
                "available": bool(os.getenv("OPENAI_API_KEY")),
                "label": "Plain-English AI — paid",
                "model": os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
            },
        },
    }


def _safe_library_path(relative_path: str) -> Path:
    candidate = (LIBRARY_ROOT / relative_path).resolve()
    try:
        candidate.relative_to(LIBRARY_ROOT.resolve())
    except ValueError as exc:
        raise WorkspaceDataError("library entry points outside the library") from exc
    return candidate


def load_library_documents(entry_ids: list[str]) -> tuple[SourceDocument, ...]:
    """Load selected pinned sources after validating their recorded checksums."""
    catalog = load_catalog()
    entries = {
        entry["id"]: entry
        for entry in catalog["entries"]
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }
    documents: list[SourceDocument] = []
    for entry_id in entry_ids:
        entry = entries.get(entry_id)
        if entry is None:
            raise WorkspaceDataError(f"unknown library entry: {entry_id}")
        relative_path = entry.get("path")
        expected_hash = entry.get("sha256")
        if not isinstance(relative_path, str) or not isinstance(expected_hash, str):
            raise WorkspaceDataError(f"invalid library entry: {entry_id}")
        path = _safe_library_path(relative_path)
        try:
            actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise WorkspaceDataError(
                f"library source is unavailable: {entry_id}"
            ) from exc
        if actual_hash != expected_hash:
            raise WorkspaceDataError(
                f"library checksum mismatch for {entry_id}; restore the pinned source"
            )
        documents.extend(load_documents([path], base_dir=PROJECT_ROOT))
    return tuple(documents)


def uploaded_documents(files: object) -> tuple[SourceDocument, ...]:
    """Validate browser-supplied UTF-8 text without persisting it."""
    if not isinstance(files, list):
        raise WorkspaceDataError("files must be a list")
    if len(files) > MAX_UPLOAD_FILES:
        raise WorkspaceDataError(f"upload at most {MAX_UPLOAD_FILES} files at once")

    documents: list[SourceDocument] = []
    total_chars = 0
    names: set[str] = set()
    for item in files:
        if not isinstance(item, dict):
            raise WorkspaceDataError("every uploaded file must include a name and text")
        name = item.get("name")
        text = item.get("text")
        if not isinstance(name, str) or not isinstance(text, str):
            raise WorkspaceDataError("every uploaded file must include a name and text")
        safe_name = Path(name).name
        if safe_name != name or not safe_name or len(safe_name) > 128:
            raise WorkspaceDataError(f"unsafe uploaded filename: {name!r}")
        if Path(safe_name).suffix.lower() not in SUPPORTED_SUFFIXES:
            supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
            raise WorkspaceDataError(
                f"unsupported uploaded file: {safe_name}; use {supported}"
            )
        if safe_name.casefold() in names:
            raise WorkspaceDataError(f"duplicate uploaded filename: {safe_name}")
        names.add(safe_name.casefold())
        total_chars += len(text)
        if total_chars > MAX_UPLOAD_CHARS:
            raise WorkspaceDataError("uploaded document text exceeds the 5 MB limit")
        try:
            documents.append(document_from_text(f"uploads/{safe_name}", text))
        except ValueError as exc:
            raise WorkspaceDataError(str(exc)) from exc
    return tuple(documents)


def build_session(payload: object) -> WorkspaceSession:
    """Build a deterministic in-memory index from library and uploaded sources."""
    if not isinstance(payload, dict):
        raise WorkspaceDataError("request body must be a JSON object")
    library_ids = payload.get("library_ids", [])
    if not isinstance(library_ids, list) or not all(
        isinstance(value, str) for value in library_ids
    ):
        raise WorkspaceDataError("library_ids must be a list of strings")
    documents = load_library_documents(library_ids) + uploaded_documents(
        payload.get("files", [])
    )
    if not documents:
        raise WorkspaceDataError("select a library source or upload at least one file")
    knowledge_base = QAKnowledgeBase.from_documents(documents)
    return WorkspaceSession(
        assistant=QAAssistant(knowledge_base, ExtractiveGenerator()),
        sources=tuple(document.source for document in documents),
    )


def _result_matches(result: SearchResult, expected_id: str) -> bool:
    searchable = f"{result.chunk.heading}\n{result.chunk.text}".casefold()
    return expected_id.casefold() in searchable


def _result_data(result: SearchResult, rank: int) -> dict[str, object]:
    identifiers = _EVIDENCE_ID.findall(f"{result.chunk.heading}\n{result.chunk.text}")
    return {
        "rank": rank,
        "score": round(result.score, 4),
        "source": result.chunk.source,
        "heading": result.chunk.heading,
        "text": result.chunk.text,
        "evidence_ids": list(
            dict.fromkeys(identifier.lower() for identifier in identifiers)
        ),
    }


def _metric(
    name: str,
    value: float | bool | None,
    display: str,
    criterion: str,
    meaning: str,
) -> dict[str, object]:
    return {
        "name": name,
        "value": value,
        "display": display,
        "criterion": criterion,
        "meaning": meaning,
    }


def _answer_generator(answer_mode: str, *, confirm_paid: bool) -> AnswerGenerator:
    if answer_mode == EVIDENCE_MODE:
        return ExtractiveGenerator()
    if answer_mode == LOCAL_AI_MODE:
        load_dotenv()
        try:
            return OllamaGenerator(
                model=os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
                base_url=os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
            )
        except (OllamaAdapterError, ValueError) as exc:
            raise WorkspaceDataError(str(exc)) from exc
    if answer_mode != PLAIN_ENGLISH_MODE:
        raise WorkspaceDataError(f"unknown answer mode: {answer_mode}")
    if not confirm_paid:
        raise WorkspaceDataError(
            "plain-English AI mode requires confirmation for this paid request"
        )

    load_dotenv()
    try:
        return OpenAIResponsesGenerator(
            model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
            reasoning_effort=os.getenv(
                "OPENAI_REASONING_EFFORT", DEFAULT_REASONING_EFFORT.value
            ),
            max_output_tokens=600,
        )
    except (OpenAIAdapterError, ValueError) as exc:
        raise WorkspaceDataError(str(exc)) from exc


def _labelled_metrics(
    answer: GroundedAnswer,
    expected_ids: list[str],
    duration_ms: float,
    *,
    answer_mode: str,
) -> list[dict[str, object]]:
    results = answer.context.results
    if not expected_ids:
        reason = "Add expected evidence IDs to measure accuracy for this question."
        metrics = [
            _metric(
                "Hit@K",
                None,
                "Not measured",
                "At least one expected source is retrieved.",
                reason,
            ),
            _metric(
                "Context precision",
                None,
                "Not measured",
                "Retrieved passages should be relevant.",
                reason,
            ),
            _metric(
                "Context recall",
                None,
                "Not measured",
                "All expected evidence should be retrieved.",
                reason,
            ),
            _metric(
                "Reciprocal rank",
                None,
                "Not measured",
                "Expected evidence should appear near the top.",
                reason,
            ),
            _metric(
                "Citation precision",
                None,
                "Not measured",
                "Cited passages should be relevant.",
                reason,
            ),
            _metric(
                "Citation recall",
                None,
                "Not measured",
                "Expected evidence should be cited.",
                reason,
            ),
        ]
    else:
        matching_ranks = [
            rank
            for rank, result in enumerate(results, start=1)
            if any(_result_matches(result, expected) for expected in expected_ids)
        ]
        found_ids = {
            expected
            for expected in expected_ids
            if any(_result_matches(result, expected) for result in results)
        }
        relevant_count = len(matching_ranks)
        hit = bool(matching_ranks)
        precision = relevant_count / len(results) if results else 0.0
        recall = len(found_ids) / len(expected_ids)
        reciprocal_rank = 1 / matching_ranks[0] if matching_ranks else 0.0

        cited_results = [
            results[citation.identifier - 1]
            for citation in answer.citations
            if citation.identifier <= len(results)
        ]
        relevant_citations = sum(
            any(_result_matches(result, expected) for expected in expected_ids)
            for result in cited_results
        )
        cited_expected = {
            expected
            for expected in expected_ids
            if any(_result_matches(result, expected) for result in cited_results)
        }
        citation_precision = (
            relevant_citations / len(cited_results) if cited_results else 0.0
        )
        citation_recall = len(cited_expected) / len(expected_ids)
        metrics = [
            _metric(
                "Hit@K",
                hit,
                "Hit" if hit else "Miss",
                f"At least one expected source must appear in the top {len(results)} results.",
                (
                    "The search found expected evidence among its first results."
                    if hit
                    else "The search did not find any expected evidence in its first results."
                ),
            ),
            _metric(
                "Context precision",
                precision,
                f"{precision:.0%}",
                "A larger share means less irrelevant material was retrieved.",
                f"{relevant_count} of {len(results)} retrieved passages matched an expected ID.",
            ),
            _metric(
                "Context recall",
                recall,
                f"{recall:.0%}",
                "100% means every expected evidence ID was retrieved.",
                f"The search found {len(found_ids)} of {len(expected_ids)} expected evidence IDs.",
            ),
            _metric(
                "Reciprocal rank",
                reciprocal_rank,
                f"{reciprocal_rank:.2f}",
                "1.00 means the first result was expected; lower values mean it appeared later.",
                (
                    f"The first expected passage appeared at result {matching_ranks[0]}."
                    if matching_ranks
                    else "No expected passage appeared in the retrieved results."
                ),
            ),
            _metric(
                "Citation precision",
                citation_precision,
                f"{citation_precision:.0%}",
                "100% means every answer citation points to expected evidence.",
                f"{relevant_citations} of {len(cited_results)} citations matched an expected ID.",
            ),
            _metric(
                "Citation recall",
                citation_recall,
                f"{citation_recall:.0%}",
                "100% means the answer cited every expected evidence ID.",
                f"The answer cited {len(cited_expected)} of {len(expected_ids)} expected IDs.",
            ),
        ]

    metrics.append(
        _metric(
            "Response time",
            duration_ms,
            f"{duration_ms:.2f} ms",
            "Lower is faster; this is one local run, not a production service-level promise.",
            (
                "Time used for local retrieval and the paid grounded AI response."
                if answer_mode == PLAIN_ENGLISH_MODE
                else (
                    "Time used for retrieval and local model generation on this computer."
                    if answer_mode == LOCAL_AI_MODE
                    else "Time used for local retrieval and the direct evidence excerpt."
                )
            ),
        )
    )
    return metrics


def evaluate_question(
    session: WorkspaceSession,
    *,
    question: str,
    expected_ids: object,
    top_k: int,
    answer_mode: object = EVIDENCE_MODE,
    confirm_paid: object = False,
) -> dict[str, object]:
    """Answer one question and return transparent labelled diagnostics."""
    question = question.strip()
    if not question:
        raise WorkspaceDataError("enter a question")
    if not 1 <= top_k <= 10:
        raise WorkspaceDataError("top_k must be between 1 and 10")
    if not isinstance(expected_ids, list) or not all(
        isinstance(value, str) for value in expected_ids
    ):
        raise WorkspaceDataError("expected_ids must be a list of strings")
    if not isinstance(answer_mode, str):
        raise WorkspaceDataError("answer_mode must be a string")
    if not isinstance(confirm_paid, bool):
        raise WorkspaceDataError("confirm_paid must be true or false")
    normalized_ids = list(
        dict.fromkeys(
            value.strip().casefold() for value in expected_ids if value.strip()
        )
    )

    generator = _answer_generator(answer_mode, confirm_paid=confirm_paid)
    assistant = QAAssistant(session.assistant.knowledge_base, generator)
    started = perf_counter()
    try:
        answer = assistant.answer(question, top_k=top_k)
    except (OllamaAdapterError, OpenAIAdapterError) as exc:
        raise WorkspaceDataError(str(exc)) from exc
    duration_ms = (perf_counter() - started) * 1000
    usage = getattr(generator, "last_usage", None)
    answer_text = answer.text
    if answer_mode == EVIDENCE_MODE:
        answer_text = answer_text.removeprefix(EXTRACTIVE_PREFIX)
    return {
        "question": question,
        "answer": answer_text,
        "answer_mode": answer_mode,
        "answer_heading": (
            "Cloud plain-English answer"
            if answer_mode == PLAIN_ENGLISH_MODE
            else (
                "Local plain-English answer"
                if answer_mode == LOCAL_AI_MODE
                else "Direct source excerpt"
            )
        ),
        "mode_explanation": (
            "Generated from retrieved evidence through a paid OpenAI request."
            if answer_mode == PLAIN_ENGLISH_MODE
            else (
                "Generated from retrieved evidence by the local model on this computer. "
                "Review the evidence because valid citations do not prove every "
                "claim is supported."
                if answer_mode == LOCAL_AI_MODE
                else "Copied from the first retrieved passage without AI rewriting."
            )
        ),
        "supported": answer.is_supported,
        "citations": [
            {
                "identifier": citation.identifier,
                "source": citation.source,
                "section": citation.heading,
                "display": (
                    f"[{citation.identifier}] {citation.source}, section "
                    f"“{citation.heading}”"
                ),
            }
            for citation in answer.citations
        ],
        "usage": (
            {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "total_tokens": usage.total_tokens,
                "reasoning_tokens": usage.reasoning_tokens,
            }
            if isinstance(usage, GenerationUsage)
            else None
        ),
        "expected_ids": normalized_ids,
        "metrics": _labelled_metrics(
            answer,
            normalized_ids,
            duration_ms,
            answer_mode=answer_mode,
        ),
        "results": [
            _result_data(result, rank)
            for rank, result in enumerate(answer.context.results, start=1)
        ],
    }


class WorkspaceRequestHandler(BaseHTTPRequestHandler):
    """Serve the local-only workspace and its small JSON API."""

    store = WorkspaceStore()

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json_response(self, status: HTTPStatus, data: object) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> object:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise WorkspaceDataError("invalid request size") from exc
        if length <= 0 or length > MAX_REQUEST_BYTES:
            raise WorkspaceDataError("request must be between 1 byte and 6 MB")
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise WorkspaceDataError("request body must be valid UTF-8 JSON") from exc

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            try:
                body = WORKSPACE_HTML.read_bytes()
            except OSError:
                self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'",
            )
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/library":
            try:
                self._json_response(HTTPStatus.OK, load_catalog())
            except WorkspaceDataError as exc:
                self._json_response(
                    HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)}
                )
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/index":
                session = build_session(payload)
                identifier = self.store.put(session)
                knowledge_base = session.assistant.knowledge_base
                self._json_response(
                    HTTPStatus.OK,
                    {
                        "session_id": identifier,
                        "document_count": knowledge_base.document_count,
                        "chunk_count": len(knowledge_base.chunks),
                        "sources": session.sources,
                    },
                )
                return
            if path == "/api/ask":
                if not isinstance(payload, dict):
                    raise WorkspaceDataError("request body must be a JSON object")
                identifier = payload.get("session_id")
                question = payload.get("question")
                top_k = payload.get("top_k", 3)
                if not isinstance(identifier, str) or not isinstance(question, str):
                    raise WorkspaceDataError("session_id and question are required")
                if not isinstance(top_k, int) or isinstance(top_k, bool):
                    raise WorkspaceDataError("top_k must be an integer")
                result = evaluate_question(
                    self.store.get(identifier),
                    question=question,
                    expected_ids=payload.get("expected_ids", []),
                    top_k=top_k,
                    answer_mode=payload.get("answer_mode", EVIDENCE_MODE),
                    confirm_paid=payload.get("confirm_paid", False),
                )
                self._json_response(HTTPStatus.OK, result)
                return
            self.send_error(HTTPStatus.NOT_FOUND)
        except WorkspaceDataError as exc:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except (OSError, UnicodeError, ValueError) as exc:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": str(exc)})


def run_workspace(
    *, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True
) -> None:
    """Run the local workspace until interrupted."""
    if host not in {"127.0.0.1", "localhost"}:
        raise WorkspaceDataError("the learning workspace only binds to localhost")
    server = ThreadingHTTPServer((host, port), WorkspaceRequestHandler)
    url = f"http://{host}:{server.server_port}"
    print(f"Real-data workspace: {url}")
    print("Press Ctrl+C to stop. Uploaded files stay in memory and are not saved.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
