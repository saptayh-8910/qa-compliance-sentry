import sqlite3
from pathlib import Path

import pytest

from db.seed import SCHEMA_PATH, init_db
from db.validation import DataValidator


@pytest.fixture
def validator(tmp_path: Path) -> DataValidator:
    db = tmp_path / "test.db"
    init_db(db, reset=True)
    return DataValidator(db)


@pytest.mark.db
def test_all_seed_validations_pass(validator: DataValidator) -> None:
    results = validator.run_all()
    assert all(r.passed for r in results), [r for r in results if not r.passed]


@pytest.mark.db
def test_api_db_consistency(validator: DataValidator) -> None:
    post = {"userId": 1, "id": 1, "title": "Backpack", "body": "Fixture"}
    result = validator.api_post_matches_catalog(post, product_id=1)
    assert result.passed, result.detail


@pytest.mark.db
def test_api_db_consistency_rejects_unrelated_post(
    validator: DataValidator,
) -> None:
    post = {"userId": 1, "id": 99, "title": "Unknown", "body": "Fixture"}
    result = validator.api_post_matches_catalog(post, product_id=1)
    assert not result.passed


@pytest.mark.db
def test_validator_requires_an_existing_database(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Database not found"):
        DataValidator(tmp_path / "missing.db")


@pytest.mark.db
def test_detects_orphaned_product(validator: DataValidator) -> None:
    with sqlite3.connect(validator.db_path) as conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("UPDATE orders SET product_id = 999 WHERE id = 1")

    result = validator.check_orders_reference_valid_products()
    assert not result.passed
    assert "Orphans" in result.detail


@pytest.mark.db
def test_detects_invalid_prices_and_order_values(
    validator: DataValidator,
) -> None:
    with sqlite3.connect(validator.db_path) as conn:
        conn.execute("PRAGMA ignore_check_constraints = ON")
        conn.execute("UPDATE products SET price = -1 WHERE id = 1")
        conn.execute("UPDATE orders SET quantity = 0, status = 'unknown' WHERE id = 1")

    assert not validator.check_product_prices().passed
    assert not validator.check_order_values().passed


@pytest.mark.db
def test_init_db_reuses_complete_seed(tmp_path: Path) -> None:
    db_path = tmp_path / "complete.db"
    init_db(db_path)

    assert init_db(db_path) == db_path


@pytest.mark.db
def test_init_db_rejects_partial_seed(tmp_path: Path) -> None:
    db_path = tmp_path / "partial.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO users (id, username, full_name) VALUES (?, ?, ?)",
            (1, "partial_user", "Partial User"),
        )

    with pytest.raises(RuntimeError, match="partially seeded"):
        init_db(db_path)
