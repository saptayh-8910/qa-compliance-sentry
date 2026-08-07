"""OpenAI Responses API adapter for grounded answer generation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, cast

from qa_assistant.models import GenerationRequest

DEFAULT_OPENAI_MODEL = "gpt-5.6-sol"


class ReasoningEffort(StrEnum):
    """Reasoning levels supported by the GPT-5.6 model family."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
    MAX = "max"


DEFAULT_REASONING_EFFORT = ReasoningEffort.MEDIUM


class OpenAIAdapterError(RuntimeError):
    """Base error for configuration, request, and response failures."""


class OpenAIConfigurationError(OpenAIAdapterError):
    """Raised when the OpenAI client cannot be configured securely."""


class OpenAIRequestError(OpenAIAdapterError):
    """Raised when the Responses API request fails."""


class OpenAIResponseError(OpenAIAdapterError):
    """Raised when the Responses API returns no usable answer text."""


@dataclass(frozen=True, slots=True)
class ResponseUsage:
    """Token counts returned by the Responses API when available."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    reasoning_tokens: int | None = None


class _ResponsesEndpoint(Protocol):
    def create(self, **kwargs: object) -> object:
        """Create one model response."""


class _OpenAIClient(Protocol):
    responses: _ResponsesEndpoint


class OpenAIResponsesGenerator:
    """Generate grounded answers through OpenAI's Responses API."""

    def __init__(
        self,
        *,
        model: str = DEFAULT_OPENAI_MODEL,
        reasoning_effort: ReasoningEffort | str = DEFAULT_REASONING_EFFORT,
        max_output_tokens: int = 600,
        client: _OpenAIClient | None = None,
    ) -> None:
        if not model.strip():
            raise ValueError("model cannot be empty")
        if max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive")
        try:
            selected_effort = ReasoningEffort(reasoning_effort)
        except ValueError as exc:
            valid = ", ".join(effort.value for effort in ReasoningEffort)
            raise ValueError(f"reasoning_effort must be one of: {valid}") from exc

        self.model = model
        self.reasoning_effort = selected_effort
        self.max_output_tokens = max_output_tokens
        self.client = client or self._default_client()
        self.last_usage: ResponseUsage | None = None

    @staticmethod
    def _default_client() -> _OpenAIClient:
        if not os.getenv("OPENAI_API_KEY"):
            raise OpenAIConfigurationError(
                "OPENAI_API_KEY is missing; add it to the local .env file"
            )
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise OpenAIConfigurationError(
                "OpenAI SDK is not installed; run `pip install -e .`"
            ) from exc
        return cast(_OpenAIClient, OpenAI())

    @staticmethod
    def _build_input(request: GenerationRequest) -> str:
        return (
            "Answer the question using only the retrieved context.\n\n"
            "<question>\n"
            f"{request.question}\n"
            "</question>\n\n"
            "<retrieved_context>\n"
            f"{request.context.text}\n"
            "</retrieved_context>"
        )

    @staticmethod
    def _field(value: object, name: str) -> object | None:
        if isinstance(value, dict):
            return value.get(name)
        return getattr(value, name, None)

    @classmethod
    def _response_usage(cls, response: object) -> ResponseUsage | None:
        usage = cls._field(response, "usage")
        if usage is None:
            return None

        input_tokens = cls._field(usage, "input_tokens")
        output_tokens = cls._field(usage, "output_tokens")
        total_tokens = cls._field(usage, "total_tokens")
        if not all(
            isinstance(value, int)
            for value in (input_tokens, output_tokens, total_tokens)
        ):
            return None

        output_details = cls._field(usage, "output_tokens_details")
        reasoning_tokens = (
            cls._field(output_details, "reasoning_tokens")
            if output_details is not None
            else None
        )
        return ResponseUsage(
            input_tokens=cast(int, input_tokens),
            output_tokens=cast(int, output_tokens),
            total_tokens=cast(int, total_tokens),
            reasoning_tokens=(
                reasoning_tokens if isinstance(reasoning_tokens, int) else None
            ),
        )

    def generate(self, request: GenerationRequest) -> str:
        if not request.context.results:
            raise ValueError("generation requires retrieved context")

        self.last_usage = None
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=request.instructions,
                input=self._build_input(request),
                reasoning={"effort": self.reasoning_effort.value},
                max_output_tokens=self.max_output_tokens,
                store=False,
            )
        except Exception as exc:
            raise OpenAIRequestError(f"OpenAI request failed: {exc}") from exc

        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str) or not output_text.strip():
            raise OpenAIResponseError("OpenAI response did not contain answer text")
        self.last_usage = self._response_usage(response)
        return output_text.strip()
