"""
reminders.py — Timed reminder system using python-telegram-bot's JobQueue.

Reminders are stored in SQLite for persistence across restarts and
scheduled via the JobQueue for execution. When a reminder fires,
the bot sends a Telegram message to the user.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiosqlite
from telegram.ext import ContextTypes

from app.config import DB_PATH

logger = logging.getLogger(__name__)


# ── Database setup ────────────────────────────────────────────────────────────


async def init_reminders_table() -> None:
    """Create the reminders table if it doesn't exist. Called once at startup."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT    NOT NULL,
                chat_id    INTEGER NOT NULL,
                text       TEXT    NOT NULL,
                fire_at    TEXT    NOT NULL,
                fired      INTEGER NOT NULL DEFAULT 0,
                created_at TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await db.commit()
    logger.info("Reminders table ready.")


# ── JobQueue callback ─────────────────────────────────────────────────────────


async def _reminder_callback(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback fired by the JobQueue when a reminder is due."""
    job = context.job
    chat_id = job.data["chat_id"]
    text = job.data["text"]
    reminder_id = job.data.get("reminder_id")

    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⏰ **Reminder:** {text}",
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.error("Failed to send reminder %s: %s", reminder_id, exc)
        return

    # Mark as fired in DB
    if reminder_id:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE reminders SET fired = 1 WHERE id = ?",
                    (reminder_id,),
                )
                await db.commit()
        except Exception as exc:
            logger.warning("Could not mark reminder %s as fired: %s", reminder_id, exc)

    logger.info("Reminder %s fired for chat %s: %s", reminder_id, chat_id, text[:50])


# ── Schedule a new reminder ──────────────────────────────────────────────────


async def schedule_reminder(
    user_id: int,
    chat_id: int,
    text: str,
    delay_minutes: float,
    bot_context: Optional[ContextTypes.DEFAULT_TYPE] = None,
) -> int:
    """
    Schedule a reminder that fires after delay_minutes.

    Stores in SQLite for persistence and uses the JobQueue for execution.

    Args:
        user_id:       Telegram user ID.
        chat_id:       Telegram chat ID to send the reminder to.
        text:          The reminder message.
        delay_minutes: Minutes from now to fire.
        bot_context:   python-telegram-bot context (provides job_queue).

    Returns:
        The reminder ID from the database.
    """
    fire_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)

    # Persist to SQLite
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO reminders (user_id, chat_id, text, fire_at) VALUES (?, ?, ?, ?)",
            (str(user_id), chat_id, text, fire_at.isoformat()),
        )
        reminder_id = cursor.lastrowid
        await db.commit()

    # Schedule via JobQueue
    if bot_context and hasattr(bot_context, "job_queue") and bot_context.job_queue:
        bot_context.job_queue.run_once(
            _reminder_callback,
            when=timedelta(minutes=delay_minutes),
            data={"chat_id": chat_id, "text": text, "reminder_id": reminder_id},
            name=f"reminder_{reminder_id}",
        )

    logger.info(
        "Reminder %d scheduled for user %s (%.1f min from now).",
        reminder_id, user_id, delay_minutes,
    )
    return reminder_id


# ── Reload pending reminders on startup ───────────────────────────────────────


async def load_pending_reminders(application) -> None:
    """
    On startup, reschedule any unfired reminders from the database.
    Called from main.py's on_startup / post_init hook.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, user_id, chat_id, text, fire_at "
            "FROM reminders WHERE fired = 0"
        )
        rows = await cursor.fetchall()

    now = datetime.now(timezone.utc)
    loaded = 0

    for row in rows:
        fire_at = datetime.fromisoformat(row["fire_at"])
        if fire_at.tzinfo is None:
            fire_at = fire_at.replace(tzinfo=timezone.utc)

        delay_seconds = (fire_at - now).total_seconds()
        if delay_seconds <= 0:
            delay_seconds = 2  # Already overdue — fire in 2 seconds

        application.job_queue.run_once(
            _reminder_callback,
            when=delay_seconds,
            data={
                "chat_id": int(row["chat_id"]),
                "text": row["text"],
                "reminder_id": row["id"],
            },
            name=f"reminder_{row['id']}",
        )
        loaded += 1

    if loaded:
        logger.info("Loaded %d pending reminder(s) from database.", loaded)
