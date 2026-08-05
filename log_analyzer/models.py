"""Domain models for structured QA logs and analysis reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

FAILURE_LEVELS = frozenset({"ERROR", "CRITICAL", "FAIL", "FAILED"})


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp must be a non-empty ISO-8601 string")

    normalized = value.strip().replace("Z", "+00:00")
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"invalid ISO-8601 timestamp: {value}") from exc

    if timestamp.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return timestamp.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class LogEvent:
    timestamp: datetime
    level: str
    message: str
    test_name: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LogEvent:
        level = data.get("level")
        message = data.get("message")
        test_name = data.get("test_name")

        if not isinstance(level, str) or not level.strip():
            raise ValueError("level must be a non-empty string")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("message must be a non-empty string")
        if test_name is not None and not isinstance(test_name, str):
            raise ValueError("test_name must be a string when provided")
        normalized_test_name = test_name.strip() if test_name else ""

        return cls(
            timestamp=_parse_timestamp(data.get("timestamp")),
            level=level.strip().upper(),
            message=message.strip(),
            test_name=normalized_test_name or None,
        )

    @property
    def is_failure(self) -> bool:
        return self.level in FAILURE_LEVELS


@dataclass(frozen=True, slots=True)
class FailureSummary:
    signature: str
    count: int
    first_seen: datetime
    last_seen: datetime
    tests: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IncidentWindow:
    start: datetime
    end: datetime
    event_count: int


@dataclass(frozen=True, slots=True)
class AnalysisReport:
    total_events: int
    failure_events: int
    top_failures: tuple[FailureSummary, ...]
    incidents: tuple[IncidentWindow, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
