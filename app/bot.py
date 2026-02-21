"""
bot.py — Telegram bot handlers.

Handlers registered here:
  /start   — welcome message
  /help    — command list
  /reset   — wipe the user's conversation memory
  <text>   — normal message → Ollama response
  <photo>  — image input → Ollama vision model analysis

Each handler is fully async and logs meaningful context for debugging.
An `authorized_only` decorator restricts access to allowed Telegram user IDs.
"""

import base64
import logging
from functools import wraps
from io import BytesIO

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
        "Send me *text* and I'll respond!\n"
        "Send me a *photo* and I'll analyze it! 📷",
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


# ── Message Handlers ──────────────────────────────────────────────────────────


async def _send_reply(update: Update, reply: str) -> None:
    """Send a reply, splitting if it exceeds Telegram's 4096-char limit."""
    if len(reply) <= 4096:
        await update.message.reply_text(  # type: ignore[union-attr]
            reply, parse_mode=ParseMode.MARKDOWN
        )
    else:
        chunks = [reply[i : i + 4096] for i in range(0, len(reply), 4096)]
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)


@authorized_only
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Text handler: receives a user message, queries Ollama, and replies.
    """
    user_id = update.effective_user.id  # type: ignore[union-attr]
    user_text = update.message.text  # type: ignore[union-attr]

    if not user_text:
        return

    logger.info("Message from user %s: %.80s", user_id, user_text)
    await _send_typing(update)

    history = await memory.get_history(user_id)
    user_msg = {"role": "user", "content": user_text}
    history.append(user_msg)

    try:
        reply = await ai_client.get_ai_response(history)
    except Exception:
        await update.message.reply_text(  # type: ignore[union-attr]
            "⚠️ Sorry, I ran into an issue reaching my AI backend. "
            "Please try again in a moment."
        )
        return

    await memory.append_messages(
        user_id,
        [user_msg, {"role": "assistant", "content": reply}],
    )
    await _send_reply(update, reply)


@authorized_only
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Photo handler: downloads the image, encodes it, and sends it
    to Ollama's vision model for analysis.
    """
    user_id = update.effective_user.id  # type: ignore[union-attr]
    caption = update.message.caption or "What's in this image? Describe it in detail."  # type: ignore[union-attr]

    logger.info("Photo from user %s (caption: %.80s)", user_id, caption)
    await _send_typing(update)

    # Download the highest resolution version of the photo
    photo = update.message.photo[-1]  # type: ignore[union-attr]  # largest size
    file = await photo.get_file()

    buf = BytesIO()
    await file.download_to_memory(buf)
    image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    logger.debug("Image downloaded — %d bytes, base64 length %d.", buf.tell(), len(image_b64))

    # Build history with the caption as user message
    history = await memory.get_history(user_id)
    user_msg = {"role": "user", "content": f"[📷 Image attached] {caption}"}
    history.append(user_msg)

    try:
        reply = await ai_client.get_ai_response(history, image_b64=image_b64)
    except Exception:
        await update.message.reply_text(  # type: ignore[union-attr]
            "⚠️ Sorry, I couldn't analyze that image. "
            "Please try again in a moment."
        )
        return

    await memory.append_messages(
        user_id,
        [user_msg, {"role": "assistant", "content": reply}],
    )
    await _send_reply(update, reply)


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

    # Register message handlers
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    app.add_handler(
        MessageHandler(filters.PHOTO, handle_photo)
    )

    # Register global error handler
    app.add_error_handler(error_handler)

    logger.info("Application built — handlers registered.")
    return app
