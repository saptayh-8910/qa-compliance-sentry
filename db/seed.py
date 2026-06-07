from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
DEFAULT_DB = Path(__file__).parent / "sentry_test.db"

SEED_USERS = [
    (1, "standard_user", "Standard User"),
    (2, "locked_out_user", "Locked Out User"),
]

SEED_PRODUCTS = [
    (1, "backpack", "Sauce Labs Backpack", 29.99),
    (2, "bike-light", "Sauce Labs Bike Light", 9.99),
    (3, "bolt-tshirt", "Sauce Labs Bolt T-Shirt", 15.99),
]

SEED_ORDERS = [
    (1, 1, 1, "completed"),
    (1, 2, 1, "pending"),
]


def init_db(db_path: Path = DEFAULT_DB, *, reset: bool = False) -> Path:
    if reset and db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        if _is_seeded(conn):
            return db_path
        conn.executemany(
            "INSERT INTO users (id, username, full_name) VALUES (?, ?, ?)",
            SEED_USERS,
        )
        conn.executemany(
            "INSERT INTO products (id, sku, name, price) VALUES (?, ?, ?, ?)",
            SEED_PRODUCTS,
        )
        conn.executemany(
            "INSERT INTO orders (user_id, product_id, quantity, status) VALUES (?, ?, ?, ?)",
            SEED_ORDERS,
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


def _is_seeded(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
    return bool(row and row[0] > 0)
