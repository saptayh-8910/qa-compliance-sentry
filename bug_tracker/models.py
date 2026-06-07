from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class BugStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class BugSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Bug:
    title: str
    description: str = ""
    status: BugStatus = BugStatus.OPEN
    severity: BugSeverity = BugSeverity.MEDIUM
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["severity"] = self.severity.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Bug:
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            status=BugStatus(data["status"]),
            severity=BugSeverity(data.get("severity", BugSeverity.MEDIUM.value)),
            created_at=data["created_at"],
            updated_at=data.get("updated_at"),
        )
