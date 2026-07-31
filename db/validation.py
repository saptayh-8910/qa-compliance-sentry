from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from db.seed import DEFAULT_DB


@dataclass
class ValidationResult:
    name: str
    passed: bool
    detail: str = ""


class DataValidator:
    """SQL consistency checks for Stage 1 data validation suite."""

    def __init__(self, db_path: Path = DEFAULT_DB) -> None:
        self.db_path = db_path
        if not db_path.is_file():
            raise FileNotFoundError(f"Database not found: {db_path}")

    def _conn(self) -> sqlite3.Connection:
        uri = f"{self.db_path.resolve().as_uri()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.execute("PRAGMA foreign_keys = ON")
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

    def check_orders_reference_valid_products(self) -> ValidationResult:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT o.id
                FROM orders o
                LEFT JOIN products p ON o.product_id = p.id
                WHERE p.id IS NULL
                """
            ).fetchall()
        passed = len(rows) == 0
        detail = "All orders have valid products" if passed else f"Orphans: {rows}"
        return ValidationResult("orders_valid_products", passed, detail)

    def check_product_prices(self) -> ValidationResult:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, price FROM products WHERE price < 0"
            ).fetchall()
        passed = len(rows) == 0
        detail = "All product prices are non-negative" if passed else f"Invalid: {rows}"
        return ValidationResult("product_prices", passed, detail)

    def check_order_values(self) -> ValidationResult:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT id, quantity, status
                FROM orders
                WHERE quantity <= 0
                   OR status NOT IN ('pending', 'completed', 'cancelled')
                """
            ).fetchall()
        passed = len(rows) == 0
        detail = "All order values are valid" if passed else f"Invalid: {rows}"
        return ValidationResult("order_values", passed, detail)

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
        """Treat the stand-in post ID as a product and verify a matching order."""
        api_user_id = api_post.get("userId")
        api_post_id = api_post.get("id")
        with self._conn() as conn:
            order = conn.execute(
                """
                SELECT o.id
                FROM orders o
                JOIN users u ON u.id = o.user_id
                JOIN products p ON p.id = o.product_id
                WHERE o.user_id = ? AND o.product_id = ?
                """,
                (api_user_id, product_id),
            ).fetchone()
        passed = api_post_id == product_id and order is not None
        detail = (
            f"API post {api_post_id} maps to product {product_id} "
            f"ordered by user {api_user_id}"
            if passed
            else (
                f"No order mapping for API user={api_user_id}, "
                f"post={api_post_id}, product={product_id}"
            )
        )
        return ValidationResult("api_db_consistency", passed, detail)

    def run_all(self) -> list[ValidationResult]:
        return [
            self.check_no_duplicate_usernames(),
            self.check_no_duplicate_skus(),
            self.check_orders_reference_valid_users(),
            self.check_orders_reference_valid_products(),
            self.check_product_prices(),
            self.check_order_values(),
            self.check_expected_order_exists(1, 1, "completed"),
        ]
