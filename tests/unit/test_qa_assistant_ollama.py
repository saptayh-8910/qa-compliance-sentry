from __future__ import annotations

from dataclasses import dataclass

import pytest
import requests

from qa_assistant.models import (
    DocumentChunk,
    GenerationRequest,
    GenerationUsage,
    RetrievalContext,
    SearchResult,
)
from qa_assistant.ollama_generator import (
    DEFAULT_OLLAMA_MODEL,
    OllamaConfigurationError,
    OllamaGenerator,
    OllamaRequestError,
    OllamaResponseError,
)


def _request() -> GenerationRequest:
    chunk = DocumentChunk(
        source="guide.md",
        heading="Quality gates",
        text="Ruff and coverage run before merge.",
        position=0,
    )
    context = RetrievalContext(
        query="Which checks run before merge?",
        results=(SearchResult(chunk=chunk, score=2.0),),
        text="[1] guide.md :: Quality gates\nRuff and coverage run before merge.",
    )
    return GenerationRequest(
        instructions="Use only evidence and cite it.",
        question="Which checks run before merge?",
        context=context,
    )


@dataclass
class FakeResponse:
    data: object

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self.data


class FakeClient:
    def __init__(self, data: object) -> None:
        self.data = data
        self.calls: list[tuple[str, dict[str, object]]] = []

    def post(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append((url, kwargs))
        return FakeResponse(self.data)


def test_ollama_generator_sends_bounded_local_request() -> None:
    client = FakeClient(
        {
            "message": {
                "content": (
                    '{"answer":"Ruff and coverage run before merge.","citations":[1]}'
                )
            },
            "prompt_eval_count": 80,
            "eval_count": 20,
        }
    )
    generator = OllamaGenerator(client=client)

    answer = generator.generate(_request())

    assert answer == "Ruff and coverage run before merge [1]."
    assert generator.model == DEFAULT_OLLAMA_MODEL == "gemma3:1b"
    assert generator.last_usage == GenerationUsage(80, 20, 100)
    url, options = client.calls[0]
    assert url == "http://127.0.0.1:11434/api/chat"
    assert options["timeout"] == 120
    payload = options["json"]
    assert isinstance(payload, dict)
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["options"] == {
        "temperature": 0,
        "num_ctx": 4096,
        "num_predict": 160,
    }
    assert payload["format"]["required"] == ["answer", "citations"]
    messages = payload["messages"]
    assert isinstance(messages, list)
    assert messages[0]["role"] == "system"
    assert messages[0]["content"].startswith("Use only evidence and cite it.")
    assert "do not blend details" in messages[0]["content"]
    assert "<retrieved_context>" in messages[1]["content"]


@pytest.mark.parametrize(
    "invalid_url",
    [
        "https://127.0.0.1:11434",
        "http://example.com:11434",
        "http://127.0.0.1:11434/api",
    ],
)
def test_ollama_generator_rejects_nonlocal_or_path_based_urls(
    invalid_url: str,
) -> None:
    with pytest.raises(OllamaConfigurationError):
        OllamaGenerator(base_url=invalid_url, client=FakeClient({}))


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ([], "not a JSON object"),
        ({}, "did not contain answer text"),
        ({"message": {"content": " "}}, "did not contain answer text"),
        (
            {"message": {"content": "not-json"}},
            "did not contain structured answer JSON",
        ),
        (
            {"message": {"content": "{}"}},
            "did not contain an answer",
        ),
        (
            {"message": {"content": '{"answer":"Supported.","citations":[]}'}},
            "did not contain valid citations",
        ),
    ],
)
def test_ollama_generator_rejects_unusable_responses(
    data: object, message: str
) -> None:
    generator = OllamaGenerator(client=FakeClient(data))

    with pytest.raises(OllamaResponseError, match=message):
        generator.generate(_request())


def test_ollama_generator_wraps_local_connection_errors() -> None:
    class FailingClient:
        def post(self, url: str, **kwargs: object) -> FakeResponse:
            raise requests.ConnectionError("service unavailable")

    generator = OllamaGenerator(client=FailingClient())

    with pytest.raises(OllamaRequestError, match="service unavailable"):
        generator.generate(_request())


def test_ollama_generator_rejects_empty_context() -> None:
    empty_context = RetrievalContext(query="missing", results=(), text="")
    request = GenerationRequest("instructions", "question", empty_context)
    generator = OllamaGenerator(client=FakeClient({}))

    with pytest.raises(ValueError, match="requires retrieved context"):
        generator.generate(request)
