from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from db.seed import DEFAULT_DB, init_db


@dataclass
class ValidationResult:
    name: str
    passed: bool
    detail: str = ""


class DataValidator:
    """SQL consistency checks for Stage 1 data validation suite."""

    def __init__(self, db_path: Path = DEFAULT_DB) -> None:
        self.db_path = db_path
        init_db(db_path)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def check_no_duplicate_usernames(self) -> ValidationResult:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT username, COUNT(*) AS cnt
                FROM users
                GROUP BY username
                HAVING cnt > 1
                """
            ).fetchall()
        passed = len(rows) == 0
        detail = "No duplicate usernames" if passed else f"Duplicates: {rows}"
        return ValidationResult("duplicate_usernames", passed, detail)

    def check_no_duplicate_skus(self) -> ValidationResult:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT sku, COUNT(*) AS cnt
                FROM products
                GROUP BY sku
                HAVING cnt > 1
                """
            ).fetchall()
        passed = len(rows) == 0
        detail = "No duplicate SKUs" if passed else f"Duplicates: {rows}"
        return ValidationResult("duplicate_skus", passed, detail)

    def check_orders_reference_valid_users(self) -> ValidationResult:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT o.id
                FROM orders o
                LEFT JOIN users u ON o.user_id = u.id
                WHERE u.id IS NULL
                """
            ).fetchall()
        passed = len(rows) == 0
        detail = "All orders have valid users" if passed else f"Orphans: {rows}"
        return ValidationResult("orders_valid_users", passed, detail)

    def check_expected_order_exists(
        self, user_id: int, product_id: int, status: str
    ) -> ValidationResult:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT id FROM orders
                WHERE user_id = ? AND product_id = ? AND status = ?
                """,
                (user_id, product_id, status),
            ).fetchone()
        passed = row is not None
        detail = (
            f"Order user={user_id} product={product_id} status={status} found"
            if passed
            else "Expected order row missing"
        )
        return ValidationResult("expected_order", passed, detail)

    def api_post_matches_catalog(
        self, api_post: dict[str, Any], product_id: int
    ) -> ValidationResult:
        """Cross-check API payload userId maps to a seeded user and product exists."""
        with self._conn() as conn:
            user = conn.execute(
                "SELECT id FROM users WHERE id = ?", (api_post.get("userId"),)
            ).fetchone()
            product = conn.execute(
                "SELECT id, name FROM products WHERE id = ?", (product_id,)
            ).fetchone()
        passed = user is not None and product is not None
        detail = (
            f"API userId {api_post.get('userId')} and product {product_id} align with DB"
            if passed
            else "API/DB mismatch"
        )
        return ValidationResult("api_db_consistency", passed, detail)

    def run_all(self) -> list[ValidationResult]:
        return [
            self.check_no_duplicate_usernames(),
            self.check_no_duplicate_skus(),
            self.check_orders_reference_valid_users(),
            self.check_expected_order_exists(1, 1, "completed"),
        ]
