"""
memory.py — Persistent, per-user conversation memory backed by SQLite.

Schema:
    messages (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    TEXT    NOT NULL,
        role       TEXT    NOT NULL,   -- 'user' | 'assistant'
        content    TEXT    NOT NULL,
        created_at TEXT    NOT NULL DEFAULT (datetime('now'))
    )

The history for each user is capped at MAX_HISTORY messages so token usage
stays predictable. Old messages beyond the limit are pruned on each write.
"""

import logging
from typing import List, Dict

import aiosqlite

from app.config import DB_PATH, MAX_HISTORY

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Create the messages table if it doesn't exist. Call once at startup."""
    async with aiosqlite.connect(DB_PATH) as db:
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
        await db.commit()
    logger.info("Database initialised at '%s'.", DB_PATH)


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
