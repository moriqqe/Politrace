"""
Database connection layer for Politrace dashboards (Capstone 3).

Uses Python's built-in ``sqlite3`` module to connect to the SQLite database
built in Capstone 2. A fresh, short-lived connection is opened per query and
closed immediately, which is thread-safe under Flask's dev server and keeps the
code dependency-free (no SQLAlchemy / driver version issues on new Pythons).

All analytical queries live in queries.py and are executed through here with
named bound parameters (``:name`` style — natively supported by sqlite3), so
there is no string interpolation of user input and no SQL-injection surface.
"""

import sqlite3
from pathlib import Path

# capstone3/backend/db.py -> capstone3/
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "politrace.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row          # rows behave like dicts
    return conn


def fetch_all(sql: str, params: dict | None = None) -> list[dict]:
    """Run a SELECT and return a list of dict rows."""
    conn = _connect()
    try:
        cur = conn.execute(sql, params or {})
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def fetch_one(sql: str, params: dict | None = None) -> dict | None:
    rows = fetch_all(sql, params)
    return rows[0] if rows else None
