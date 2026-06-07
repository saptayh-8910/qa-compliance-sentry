from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from bug_tracker.models import Bug, BugStatus


class BugStorage:
    """JSON-backed bug persistence."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _ensure_file(self) -> None:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("[]", encoding="utf-8")

    def load_all(self) -> list[Bug]:
        self._ensure_file()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return [Bug.from_dict(item) for item in raw]

    def save_all(self, bugs: Iterable[Bug]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [bug.to_dict() for bug in bugs]
        self.path.write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )

    def add(self, bug: Bug) -> Bug:
        bugs = self.load_all()
        bugs.append(bug)
        self.save_all(bugs)
        return bug

    def get(self, bug_id: str) -> Bug | None:
        return next((b for b in self.load_all() if b.id == bug_id), None)

    def update_status(self, bug_id: str, status: BugStatus) -> Bug:
        bugs = self.load_all()
        for bug in bugs:
            if bug.id == bug_id:
                bug.status = status
                from datetime import datetime, timezone

                bug.updated_at = datetime.now(timezone.utc).isoformat()
                self.save_all(bugs)
                return bug
        raise KeyError(f"Bug not found: {bug_id}")

    def search(self, query: str) -> list[Bug]:
        q = query.lower()
        return [
            b
            for b in self.load_all()
            if q in b.title.lower()
            or q in b.description.lower()
            or q in b.status.value
            or q in b.severity.value
        ]
