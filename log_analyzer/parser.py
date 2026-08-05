"""Parser for newline-delimited JSON QA logs."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from log_analyzer.models import LogEvent


def parse_json_lines(lines: Iterable[str]) -> list[LogEvent]:
    events: list[LogEvent] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_number}: invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"line {line_number}: expected a JSON object")
        try:
            events.append(LogEvent.from_dict(payload))
        except ValueError as exc:
            raise ValueError(f"line {line_number}: {exc}") from exc
    return events


def load_json_lines(path: Path) -> list[LogEvent]:
    if not path.is_file():
        raise FileNotFoundError(f"log file does not exist: {path}")
    with path.open(encoding="utf-8") as log_file:
        return parse_json_lines(log_file)
