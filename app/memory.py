"""
memory.py — Persistent, per-user conversation memory backed by SQLite.

Tables:
    messages — rolling conversation history (capped at MAX_HISTORY)
    long_term_memory — permanent key-value store for user preferences,
                       deadlines, contacts, and other persistent facts.
"""

import logging
from typing import List, Dict, Optional

import aiosqlite

from app.config import DB_PATH, MAX_HISTORY

logger = logging.getLogger(__name__)


# ── Database initialisation ──────────────────────────────────────────────────


async def init_db() -> None:
    """Create all required tables. Call once at startup."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Conversation history
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT    NOT NULL,
                role       TEXT    NOT NULL,
                content    TEXT    NOT NULL,
                created_at TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_user
            ON messages (user_id, id)
        """)

        # Long-term memory (key-value per user)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS long_term_memory (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT    NOT NULL,
                key        TEXT    NOT NULL,
                value      TEXT    NOT NULL,
                created_at TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_ltm_user_key
            ON long_term_memory (user_id, key)
        """)

        await db.commit()
    logger.info("Database initialised at '%s'.", DB_PATH)


# ── Conversation history ─────────────────────────────────────────────────────


async def get_history(user_id: int) -> List[Dict[str, str]]:
    """
    Return the last MAX_HISTORY messages for a given Telegram user_id.
    Returns a list of {"role": ..., "content": ...} dicts ready for the API.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT role, content
            FROM messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (str(user_id), MAX_HISTORY),
        )
        rows = await cursor.fetchall()

    # Rows come newest-first, reverse to chronological order
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


async def append_messages(
    user_id: int,
    new_messages: List[Dict[str, str]],
) -> None:
    """
    Insert one or more messages for a user, then prune old rows beyond
    MAX_HISTORY to keep the table compact.
    """
    key = str(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executemany(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            [(key, m["role"], m["content"]) for m in new_messages],
        )

        # Prune: keep only the newest MAX_HISTORY rows for this user
        await db.execute(
            """
            DELETE FROM messages
            WHERE user_id = ?
              AND id NOT IN (
                  SELECT id FROM messages
                  WHERE user_id = ?
                  ORDER BY id DESC
                  LIMIT ?
              )
            """,
            (key, key, MAX_HISTORY),
        )
        await db.commit()

    logger.debug("Memory updated for user %s.", user_id)


async def clear_history(user_id: int) -> None:
    """Wipe the conversation history for a user (useful for /reset command)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM messages WHERE user_id = ?",
            (str(user_id),),
        )
        await db.commit()
    logger.info("Cleared history for user %s.", user_id)


# ── Long-term memory ─────────────────────────────────────────────────────────


async def store_long_term(user_id: int, key: str, value: str) -> None:
    """
    Store or update a long-term memory for a user.
    If the key already exists, the old value is replaced.
    """
    uid = str(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        # Upsert: remove old value for the same key, then insert new
        await db.execute(
            "DELETE FROM long_term_memory WHERE user_id = ? AND key = ?",
            (uid, key),
        )
        await db.execute(
            "INSERT INTO long_term_memory (user_id, key, value) VALUES (?, ?, ?)",
            (uid, key, value),
        )
        await db.commit()
    logger.debug("Stored long-term memory for user %s: %s", user_id, key)


async def retrieve_long_term(user_id: int, key: str) -> Optional[str]:
    """Retrieve a specific long-term memory by key. Returns None if not found."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT value FROM long_term_memory WHERE user_id = ? AND key = ?",
            (str(user_id), key),
        )
        row = await cursor.fetchone()
    return row[0] if row else None


async def list_long_term(user_id: int) -> List[tuple]:
    """List all stored memories for a user as (key, value) pairs."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT key, value FROM long_term_memory WHERE user_id = ? ORDER BY key",
            (str(user_id),),
        )
        rows = await cursor.fetchall()
    return [(row[0], row[1]) for row in rows]
