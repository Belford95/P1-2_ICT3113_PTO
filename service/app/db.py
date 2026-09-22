"""SQLite storage. Baseline: a new connection per call, no indexes beyond the PK."""
import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "/data/tickets.db")


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with connect() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                narrative TEXT NOT NULL,
                category TEXT NOT NULL,
                model TEXT NOT NULL,
                source_row INTEGER,
                run_id TEXT
            )"""
        )


def insert(created_at, narrative, category, model, source_row, run_id):
    with connect() as c:
        cur = c.execute(
            "INSERT INTO tickets (created_at, narrative, category, model, source_row, run_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (created_at, narrative, category, model, source_row, run_id),
        )
        return cur.lastrowid


def search(q, limit):
    with connect() as c:
        rows = c.execute(
            "SELECT id, created_at, category, source_row, narrative FROM tickets "
            "WHERE narrative LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{q}%", limit),
        ).fetchall()
    return [dict(r) for r in rows]


def stats():
    with connect() as c:
        rows = c.execute("SELECT category, COUNT(*) AS n FROM tickets GROUP BY category").fetchall()
    return {r["category"]: r["n"] for r in rows}


def clear():
    with connect() as c:
        n = c.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        c.execute("DELETE FROM tickets")
    return n
