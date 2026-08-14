"""Local Ollama adapter for citation-grounded answer generation."""

from __future__ import annotations

import json
import re
from typing import Protocol, cast
from urllib.parse import urlparse

import requests

from qa_assistant.models import GenerationRequest, GenerationUsage

DEFAULT_OLLAMA_MODEL = "gemma3:1b"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
LOCAL_GROUNDING_ADDENDUM = """Small local-model rules:
- answer only the question that was asked, in at most two concise sentences
- treat each numbered context passage as separate evidence
- do not blend details from neighboring requirements
- list every passage whose facts you use in the structured citations field
- do not repeat source paths, headings, requirement labels, or context blocks
"""


class OllamaAdapterError(RuntimeError):
    """Base error for local configuration, request, and response failures."""


class OllamaConfigurationError(OllamaAdapterError):
    """Raised when the local Ollama endpoint is configured unsafely."""


class OllamaRequestError(OllamaAdapterError):
    """Raised when the local Ollama request cannot complete."""


class OllamaResponseError(OllamaAdapterError):
    """Raised when Ollama returns no usable answer text."""


class _HTTPResponse(Protocol):
    def raise_for_status(self) -> None:
        """Raise when the response is unsuccessful."""

    def json(self) -> object:
        """Decode the response body."""


class _HTTPClient(Protocol):
    def post(self, url: str, **kwargs: object) -> _HTTPResponse:
        """Send one local HTTP request."""


def _local_base_url(value: str) -> str:
    base_url = value.strip().rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }:
        raise OllamaConfigurationError(
            "OLLAMA_BASE_URL must use a local HTTP address such as "
            "http://127.0.0.1:11434"
        )
    if parsed.path or parsed.params or parsed.query or parsed.fragment:
        raise OllamaConfigurationError("OLLAMA_BASE_URL must not include a path")
    return base_url


class OllamaGenerator:
    """Generate grounded answers through a local Ollama server."""

    def __init__(
        self,
        *,
        model: str = DEFAULT_OLLAMA_MODEL,
        base_url: str = DEFAULT_OLLAMA_BASE_URL,
        max_output_tokens: int = 160,
        context_tokens: int = 4_096,
        timeout_seconds: float = 120,
        client: _HTTPClient | None = None,
    ) -> None:
        if not model.strip():
            raise ValueError("model cannot be empty")
        if max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive")
        if context_tokens < 512:
            raise ValueError("context_tokens must be at least 512")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        self.model = model.strip()
        self.base_url = _local_base_url(base_url)
        self.max_output_tokens = max_output_tokens
        self.context_tokens = context_tokens
        self.timeout_seconds = timeout_seconds
        self.client = client or requests.Session()
        self.last_usage: GenerationUsage | None = None

    @staticmethod
    def _user_message(request: GenerationRequest) -> str:
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
    def _usage(data: dict[str, object]) -> GenerationUsage | None:
        input_tokens = data.get("prompt_eval_count")
        output_tokens = data.get("eval_count")
        if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
            return None
        return GenerationUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )

    def generate(self, request: GenerationRequest) -> str:
        if not request.context.results:
            raise ValueError("generation requires retrieved context")

        self.last_usage = None
        try:
            response = self.client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                f"{request.instructions}\n\n{LOCAL_GROUNDING_ADDENDUM}"
                            ),
                        },
                        {"role": "user", "content": self._user_message(request)},
                    ],
                    "stream": False,
                    "think": False,
                    "keep_alive": "2m",
                    "format": {
                        "type": "object",
                        "properties": {
                            "answer": {
                                "type": "string",
                                "description": (
                                    "A concise plain-English answer without source "
                                    "paths or copied context blocks."
                                ),
                            },
                            "citations": {
                                "type": "array",
                                "description": (
                                    "The numbered retrieved passages supporting "
                                    "the answer."
                                ),
                                "items": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": len(request.context.results),
                                },
                                "minItems": 1,
                                "maxItems": len(request.context.results),
                                "uniqueItems": True,
                            },
                        },
                        "required": ["answer", "citations"],
                        "additionalProperties": False,
                    },
                    "options": {
                        "temperature": 0,
                        "num_ctx": self.context_tokens,
                        "num_predict": self.max_output_tokens,
                    },
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise OllamaRequestError(
                f"Local Ollama request failed: {exc}. Ensure Ollama is running "
                f"and `{self.model}` is installed."
            ) from exc

        if not isinstance(data, dict):
            raise OllamaResponseError("Ollama response was not a JSON object")
        message = data.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise OllamaResponseError("Ollama response did not contain answer text")
        try:
            structured = json.loads(content)
        except json.JSONDecodeError as exc:
            raise OllamaResponseError(
                "Ollama response did not contain structured answer JSON"
            ) from exc
        answer = structured.get("answer") if isinstance(structured, dict) else None
        if not isinstance(answer, str) or not answer.strip():
            raise OllamaResponseError(
                "Ollama structured response did not contain an answer"
            )
        citations = structured.get("citations")
        available = len(request.context.results)
        if (
            not isinstance(citations, list)
            or not citations
            or not all(
                isinstance(identifier, int)
                and not isinstance(identifier, bool)
                and 1 <= identifier <= available
                for identifier in citations
            )
        ):
            raise OllamaResponseError(
                "Ollama structured response did not contain valid citations"
            )
        self.last_usage = self._usage(cast(dict[str, object], data))
        clean_answer = re.sub(r"\[\d+]", "", answer).strip()
        if not clean_answer:
            raise OllamaResponseError(
                "Ollama structured response did not contain answer text"
            )
        citation_text = " ".join(
            f"[{identifier}]" for identifier in dict.fromkeys(citations)
        )
        punctuation = clean_answer[-1] if clean_answer[-1] in ".!?" else ""
        answer_body = clean_answer[:-1].rstrip() if punctuation else clean_answer
        return f"{answer_body} {citation_text}{punctuation}"
