from pathlib import Path

import pytest

from bug_tracker.models import Bug, BugSeverity, BugStatus
from bug_tracker.storage import BugStorage


@pytest.fixture
def storage(tmp_path: Path) -> BugStorage:
    return BugStorage(tmp_path / "bugs.json")


def test_add_and_list(storage: BugStorage) -> None:
    bug = Bug(title="Login button unresponsive", severity=BugSeverity.HIGH)
    storage.add(bug)
    bugs = storage.load_all()
    assert len(bugs) == 1
    assert bugs[0].title == "Login button unresponsive"
    assert bugs[0].severity == BugSeverity.HIGH


def test_update_status(storage: BugStorage) -> None:
    bug = Bug(title="Cart total wrong")
    storage.add(bug)
    updated = storage.update_status(bug.id, BugStatus.IN_PROGRESS)
    assert updated.status == BugStatus.IN_PROGRESS
    assert updated.updated_at is not None


def test_search_by_title(storage: BugStorage) -> None:
    storage.add(Bug(title="Checkout timeout", description="On slow network"))
    storage.add(Bug(title="Typo in footer"))
    results = storage.search("checkout")
    assert len(results) == 1
    assert results[0].title == "Checkout timeout"


def test_update_missing_raises(storage: BugStorage) -> None:
    with pytest.raises(KeyError):
        storage.update_status("missing-id", BugStatus.CLOSED)


def test_persistence_roundtrip(storage: BugStorage) -> None:
    storage.add(Bug(title="Flaky test on CI"))
    reloaded = BugStorage(storage.path)
    assert len(reloaded.load_all()) == 1
