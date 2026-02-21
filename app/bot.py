"""
bot.py — Telegram bot handlers.

Handlers registered here:
  /start   — welcome message
  /help    — command list
  /reset   — wipe the user's conversation memory
  <text>   — normal message → Claude response

Each handler is fully async and logs meaningful context for debugging.
An `authorized_only` decorator restricts access to allowed Telegram user IDs.
"""

import logging
from functools import wraps

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from app import memory, ai_client
from app.config import TELEGRAM_BOT_TOKEN, ALLOWED_USER_IDS

logger = logging.getLogger(__name__)


# ── Authorization ─────────────────────────────────────────────────────────────


def authorized_only(handler):
    """
    Decorator that restricts a handler to users in ALLOWED_USER_IDS.
    If the allow-list is empty, everyone is permitted (open mode).
    """
    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if ALLOWED_USER_IDS:
            user_id = update.effective_user.id  # type: ignore[union-attr]
            if user_id not in ALLOWED_USER_IDS:
                logger.warning(
                    "Unauthorized access attempt by user %s (@%s).",
                    user_id,
                    getattr(update.effective_user, "username", "unknown"),
                )
                await update.message.reply_text(  # type: ignore[union-attr]
                    "⛔ Access denied — you are not authorized to use this bot."
                )
                return
        return await handler(update, context)
    return wrapper


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _send_typing(update: Update) -> None:
    """Show the 'typing…' indicator so the user knows the bot is working."""
    await update.effective_chat.send_action(ChatAction.TYPING)  # type: ignore[union-attr]


# ── Command Handlers ──────────────────────────────────────────────────────────


@authorized_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the user starts the bot."""
    user = update.effective_user
    await update.message.reply_text(  # type: ignore[union-attr]
        f"👋 Hi {user.first_name}! I'm *Aria*, your personal AI assistant.\n\n"
        "I can help you with tasks, research, writing, brainstorming, and more.\n\n"
        "Just send me a message to get started, or use /help to see all commands.",
        parse_mode=ParseMode.MARKDOWN,
    )


@authorized_only
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List available commands."""
    await update.message.reply_text(  # type: ignore[union-attr]
        "*Available commands*\n\n"
        "/start — introduce yourself\n"
        "/help  — show this message\n"
        "/reset — clear our conversation history\n\n"
        "Otherwise, just type anything and I'll respond!",
        parse_mode=ParseMode.MARKDOWN,
    )


@authorized_only
async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear the user's stored conversation history."""
    user_id = update.effective_user.id  # type: ignore[union-attr]
    await memory.clear_history(user_id)
    await update.message.reply_text(  # type: ignore[union-attr]
        "🗑️ Done — I've cleared our conversation history. Fresh start!"
    )
    logger.info("User %s reset their history.", user_id)


# ── Message Handler ───────────────────────────────────────────────────────────


@authorized_only
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Main handler: receives a user message, queries Claude, and replies.

    Flow:
      1. Load user's history from the database.
      2. Append the new user message.
      3. Send full history to Claude.
      4. Append Claude's reply.
      5. Persist updated history.
      6. Send reply to Telegram.
    """
    user_id = update.effective_user.id  # type: ignore[union-attr]
    user_text = update.message.text  # type: ignore[union-attr]

    if not user_text:
        return  # ignore non-text messages (stickers, photos, etc.)

    logger.info("Message from user %s: %.80s", user_id, user_text)

    # Show typing indicator while we fetch the response
    await _send_typing(update)

    # 1. Load existing history
    history = await memory.get_history(user_id)

    # 2. Append the user's new message to history
    user_msg = {"role": "user", "content": user_text}
    history.append(user_msg)

    try:
        # 3. Get Claude's response
        reply = await ai_client.get_ai_response(history)
    except Exception:
        # Surface a friendly error without leaking internals
        await update.message.reply_text(  # type: ignore[union-attr]
            "⚠️ Sorry, I ran into an issue reaching my AI backend. "
            "Please try again in a moment."
        )
        return

    # 4 & 5. Persist both turns together
    await memory.append_messages(
        user_id,
        [user_msg, {"role": "assistant", "content": reply}],
    )

    # 6. Reply — Telegram truncates messages over 4096 chars, so split if needed
    if len(reply) <= 4096:
        await update.message.reply_text(  # type: ignore[union-attr]
            reply, parse_mode=ParseMode.MARKDOWN
        )
    else:
        # Split on newline boundaries to preserve readability
        chunks = [reply[i : i + 4096] for i in range(0, len(reply), 4096)]
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)


# ── Error Handler ─────────────────────────────────────────────────────────────


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log unexpected errors raised inside handlers."""
    logger.error("Unhandled exception in handler:", exc_info=context.error)


# ── Application Factory ───────────────────────────────────────────────────────


def build_application() -> Application:
    """
    Construct and configure the python-telegram-bot Application.
    Called once from main.py.
    """
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    # Register command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("reset", cmd_reset))

    # Register message handler (text only, ignore bot's own messages)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Register global error handler
    app.add_error_handler(error_handler)

    logger.info("Application built — handlers registered.")
    return app
