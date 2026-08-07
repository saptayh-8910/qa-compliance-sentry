from __future__ import annotations

import sys
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from qa_assistant.models import (
    DocumentChunk,
    GenerationRequest,
    RetrievalContext,
    SearchResult,
)
from qa_assistant.openai_generator import (
    DEFAULT_OPENAI_MODEL,
    DEFAULT_REASONING_EFFORT,
    OpenAIConfigurationError,
    OpenAIRequestError,
    OpenAIResponseError,
    OpenAIResponsesGenerator,
    ReasoningEffort,
    ResponseUsage,
)


def _request() -> GenerationRequest:
    chunk = DocumentChunk(
        source="README.md",
        heading="Quality gates",
        text="Ruff and coverage run before merge.",
        position=0,
    )
    context = RetrievalContext(
        query="Which checks run before merge?",
        results=(SearchResult(chunk=chunk, score=2.0),),
        text="[1] README.md :: Quality gates\nRuff and coverage run before merge.",
    )
    return GenerationRequest(
        instructions="Use only evidence and cite it.",
        question="Which checks run before merge?",
        context=context,
    )


@dataclass
class FakeResponses:
    output_text: str = "Ruff and coverage run before merge [1]."

    def __post_init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.output_text)


@dataclass
class FakeClient:
    responses: FakeResponses


def test_openai_generator_sends_separated_grounded_request() -> None:
    responses = FakeResponses()
    generator = OpenAIResponsesGenerator(
        model="test-model",
        reasoning_effort="high",
        max_output_tokens=321,
        client=FakeClient(responses),
    )

    answer = generator.generate(_request())

    assert answer == "Ruff and coverage run before merge [1]."
    assert responses.calls == [
        {
            "model": "test-model",
            "instructions": "Use only evidence and cite it.",
            "input": (
                "Answer the question using only the retrieved context.\n\n"
                "<question>\nWhich checks run before merge?\n</question>\n\n"
                "<retrieved_context>\n"
                "[1] README.md :: Quality gates\n"
                "Ruff and coverage run before merge.\n"
                "</retrieved_context>"
            ),
            "reasoning": {"effort": "high"},
            "max_output_tokens": 321,
            "store": False,
        }
    ]


def test_openai_generator_records_response_usage() -> None:
    responses = FakeResponses()
    generator = OpenAIResponsesGenerator(client=FakeClient(responses))
    responses.create = lambda **kwargs: SimpleNamespace(  # type: ignore[method-assign]
        output_text="Supported [1].",
        usage=SimpleNamespace(
            input_tokens=80,
            output_tokens=20,
            total_tokens=100,
            output_tokens_details=SimpleNamespace(reasoning_tokens=7),
        ),
    )

    generator.generate(_request())

    assert generator.last_usage == ResponseUsage(80, 20, 100, 7)


def test_openai_generator_tolerates_missing_or_partial_usage() -> None:
    generator = OpenAIResponsesGenerator(client=FakeClient(FakeResponses()))

    generator.generate(_request())
    assert generator.last_usage is None

    responses = FakeResponses()
    responses.create = lambda **kwargs: SimpleNamespace(  # type: ignore[method-assign]
        output_text="Supported [1].",
        usage={"input_tokens": 80},
    )
    generator = OpenAIResponsesGenerator(client=FakeClient(responses))
    generator.generate(_request())

    assert generator.last_usage is None


def test_openai_generator_uses_current_default_model() -> None:
    generator = OpenAIResponsesGenerator(client=FakeClient(FakeResponses()))

    assert generator.model == DEFAULT_OPENAI_MODEL == "gpt-5.6-sol"
    assert generator.reasoning_effort is DEFAULT_REASONING_EFFORT


@pytest.mark.parametrize("reasoning_effort", list(ReasoningEffort))
def test_openai_generator_accepts_supported_reasoning_efforts(
    reasoning_effort: ReasoningEffort,
) -> None:
    generator = OpenAIResponsesGenerator(
        reasoning_effort=reasoning_effort,
        client=FakeClient(FakeResponses()),
    )

    assert generator.reasoning_effort is reasoning_effort


@pytest.mark.parametrize(
    ("model", "max_output_tokens", "message"),
    [
        (" ", 600, "model cannot be empty"),
        ("test-model", 0, "must be positive"),
    ],
)
def test_openai_generator_rejects_invalid_configuration(
    model: str, max_output_tokens: int, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        OpenAIResponsesGenerator(
            model=model,
            max_output_tokens=max_output_tokens,
            client=FakeClient(FakeResponses()),
        )


def test_openai_generator_rejects_unknown_reasoning_effort() -> None:
    with pytest.raises(ValueError, match="reasoning_effort must be one of"):
        OpenAIResponsesGenerator(
            reasoning_effort="extreme",
            client=FakeClient(FakeResponses()),
        )


def test_openai_generator_requires_local_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(OpenAIConfigurationError, match="OPENAI_API_KEY is missing"):
        OpenAIResponsesGenerator()


def test_openai_generator_builds_sdk_client_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeClient(FakeResponses())
    fake_module = SimpleNamespace(OpenAI=lambda: fake_client)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "openai", fake_module)

    generator = OpenAIResponsesGenerator()

    assert generator.client is fake_client


def test_openai_generator_reports_missing_sdk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "openai", None)

    with pytest.raises(OpenAIConfigurationError, match="SDK is not installed"):
        OpenAIResponsesGenerator()


@pytest.mark.parametrize("output_text", ["", "   ", None])
def test_openai_generator_rejects_empty_response(output_text: str | None) -> None:
    responses = FakeResponses()
    responses.output_text = output_text  # type: ignore[assignment]
    generator = OpenAIResponsesGenerator(client=FakeClient(responses))

    with pytest.raises(OpenAIResponseError, match="did not contain answer text"):
        generator.generate(_request())


def test_openai_generator_wraps_sdk_errors() -> None:
    class FailingResponses:
        def create(self, **kwargs: object) -> object:
            raise ConnectionError("network unavailable")

    generator = OpenAIResponsesGenerator(client=FakeClient(FailingResponses()))  # type: ignore[arg-type]

    with pytest.raises(OpenAIRequestError, match="network unavailable"):
        generator.generate(_request())


def test_openai_generator_rejects_empty_context() -> None:
    empty_context = RetrievalContext(query="missing", results=(), text="")
    request = GenerationRequest("instructions", "question", empty_context)
    generator = OpenAIResponsesGenerator(client=FakeClient(FakeResponses()))

    with pytest.raises(ValueError, match="requires retrieved context"):
        generator.generate(request)
