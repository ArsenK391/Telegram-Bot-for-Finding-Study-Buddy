"""
database.py — SQLite persistence layer.

users           : one row per registered Telegram user
user_subjects   : many-to-many: user ↔ subject
connections     : tracks who has already been introduced to whom
"""

import sqlite3
from contextlib import contextmanager
from typing import Generator

from config import DB_PATH, SUBJECTS


# Connection helper 

@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# Schema

def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id      INTEGER PRIMARY KEY,
                username     TEXT,
                display_name TEXT    NOT NULL,
                role         TEXT    NOT NULL DEFAULT 'both',   -- 'tutor' | 'learner' | 'both'
                availability TEXT    NOT NULL DEFAULT 'flexible', -- 'mornings'|'evenings'|'weekends'|'flexible'
                registered_at TEXT   NOT NULL DEFAULT (datetime('now')),
                active       INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS user_subjects (
                user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                subject TEXT    NOT NULL,
                PRIMARY KEY (user_id, subject)
            );

            CREATE TABLE IF NOT EXISTS connections (
                requester_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                target_id    INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                status       TEXT    NOT NULL DEFAULT 'pending',  -- 'pending'|'connected'|'skipped'
                created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (requester_id, target_id)
            );
        """)


# Users 

def upsert_user(user_id: int, username: str | None, display_name: str,
                role: str, availability: str) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, display_name, role, availability)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username     = excluded.username,
                display_name = excluded.display_name,
                role         = excluded.role,
                availability = excluded.availability,
                active       = 1
        """, (user_id, username, display_name, role, availability))


def get_user(user_id: int) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()


def deactivate_user(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE users SET active = 0 WHERE user_id = ?", (user_id,))


# Subjects 

def set_subjects(user_id: int, subjects: list[str]) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM user_subjects WHERE user_id = ?", (user_id,))
        conn.executemany(
            "INSERT OR IGNORE INTO user_subjects (user_id, subject) VALUES (?, ?)",
            [(user_id, s) for s in subjects],
        )


def get_subjects(user_id: int) -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT subject FROM user_subjects WHERE user_id = ?", (user_id,)
        ).fetchall()
    return [r["subject"] for r in rows]


# Matching 

def find_matches(user_id: int, limit: int = 5) -> list[sqlite3.Row]:
    """
    Return up to `limit` users who share at least one subject with `user_id`,
    excluding already-connected / skipped users and the requester themselves.
    Ordered by number of shared subjects descending.
    """
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT u.*,
                   GROUP_CONCAT(us2.subject, ', ') AS shared_subjects,
                   COUNT(us2.subject)              AS shared_count
            FROM users u
            JOIN user_subjects us2 ON us2.user_id = u.user_id
            JOIN user_subjects us1 ON us1.subject  = us2.subject
                                   AND us1.user_id = ?
            WHERE u.user_id != ?
              AND u.active   = 1
              AND u.user_id NOT IN (
                  SELECT target_id FROM connections
                  WHERE requester_id = ? AND status IN ('connected','skipped')
              )
            GROUP BY u.user_id
            ORDER BY shared_count DESC
            LIMIT ?
        """, (user_id, user_id, user_id, limit)).fetchall()
    return rows


# Connections 

def record_connection(requester_id: int, target_id: int, status: str) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO connections (requester_id, target_id, status)
            VALUES (?, ?, ?)
            ON CONFLICT(requester_id, target_id) DO UPDATE SET status = excluded.status
        """, (requester_id, target_id, status))


def get_connections(user_id: int) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("""
            SELECT u.*, c.status, c.created_at AS connected_at
            FROM connections c
            JOIN users u ON u.user_id = c.target_id
            WHERE c.requester_id = ? AND c.status = 'connected'
        """, (user_id,)).fetchall()
