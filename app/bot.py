"""
bot.py — Telegram bot handlers.

Handlers registered here:
  /start   — welcome message
  /help    — command list
  /reset   — wipe the user's conversation memory
  /search  — web search via DuckDuckGo + Gemini summary
  <text>   — normal message → Gemini response (with URL detection)
  <photo>  — image analysis via Gemini Vision
  <voice>  — voice transcription + response via Gemini
  <PDF>    — document analysis via PyPDF2 + Gemini

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


async def _safe_reply(update: Update, text: str) -> None:
    """Reply with Markdown, falling back to plain text if parsing fails."""
    try:
        if len(text) <= 4096:
            await update.message.reply_text(  # type: ignore[union-attr]
                text, parse_mode=ParseMode.MARKDOWN
            )
        else:
            chunks = [text[i : i + 4096] for i in range(0, len(text), 4096)]
            for chunk in chunks:
                await update.message.reply_text(  # type: ignore[union-attr]
                    chunk, parse_mode=ParseMode.MARKDOWN
                )
    except Exception:
        # Markdown parsing failed — send as plain text
        if len(text) <= 4096:
            await update.message.reply_text(text)  # type: ignore[union-attr]
        else:
            chunks = [text[i : i + 4096] for i in range(0, len(text), 4096)]
            for chunk in chunks:
                await update.message.reply_text(chunk)  # type: ignore[union-attr]


# ── Command Handlers ──────────────────────────────────────────────────────────


@authorized_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the user starts the bot."""
    user = update.effective_user
    await update.message.reply_text(  # type: ignore[union-attr]
        f"👋 Hi {user.first_name}! I'm *Aria*, your personal AI assistant.\n\n"
        "Here's what I can do:\n"
        "💬 Chat & answer questions\n"
        "🖼️ Analyse photos you send me\n"
        "🎙️ Transcribe & respond to voice messages\n"
        "📄 Read & analyse PDF documents\n"
        "🔍 Search the web with /search\n"
        "🔗 Summarise web pages — just send a URL\n\n"
        "Send me a message to get started, or use /help for all commands.",
        parse_mode=ParseMode.MARKDOWN,
    )


@authorized_only
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List available commands."""
    await update.message.reply_text(  # type: ignore[union-attr]
        "*Available commands*\n\n"
        "/start  — introduce yourself\n"
        "/help   — show this message\n"
        "/reset  — clear our conversation history\n"
        "/search — search the web\n\n"
        "*I also respond to:*\n"
        "📷 Photos — send an image for analysis\n"
        "🎙️ Voice — send a voice message for transcription\n"
        "📄 PDFs — send a document for analysis\n"
        "🔗 URLs — send a link and I'll summarise the page\n\n"
        "Or just type anything and I'll respond!",
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


# ── /search Command ──────────────────────────────────────────────────────────


@authorized_only
async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search the web and summarise results using Gemini."""
    from app import web_search

    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text(  # type: ignore[union-attr]
            "Usage: `/search your query here`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    logger.info("Search request from user %s: %s", update.effective_user.id, query)
    await _send_typing(update)

    # Fetch search results
    search_results = await web_search.search(query)

    # Ask Gemini to summarise the results
    user_id = update.effective_user.id  # type: ignore[union-attr]
    history = await memory.get_history(user_id)

    summary_prompt = (
        f"The user searched for: \"{query}\"\n\n"
        f"Here are the top web search results:\n\n{search_results}\n\n"
        "Provide a helpful, concise summary of these search results. "
        "Include the most relevant information and cite sources with their URLs."
    )

    user_msg = {"role": "user", "content": summary_prompt}
    history.append(user_msg)

    try:
        reply = await ai_client.get_ai_response(history)
    except Exception:
        await update.message.reply_text(  # type: ignore[union-attr]
            "⚠️ Got search results but failed to summarise them. Try again."
        )
        return

    # Persist memory
    display_msg = {"role": "user", "content": f"/search {query}"}
    await memory.append_messages(
        user_id,
        [display_msg, {"role": "assistant", "content": reply}],
    )

    await _safe_reply(update, reply)


# ── Photo Handler (Image Analysis) ───────────────────────────────────────────


@authorized_only
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download the photo, send to Gemini Vision, and reply with analysis."""
    user_id = update.effective_user.id  # type: ignore[union-attr]
    caption = update.message.caption or None  # type: ignore[union-attr]

    logger.info("Photo from user %s (caption: %s)", user_id, caption or "none")
    await _send_typing(update)

    # Download the highest-resolution photo
    photo = update.message.photo[-1]  # type: ignore[union-attr]
    file = await photo.get_file()
    image_bytes = await file.download_as_bytearray()

    # Load history for context
    history = await memory.get_history(user_id)

    try:
        reply = await ai_client.get_vision_response(
            history,
            image_bytes=bytes(image_bytes),
            mime_type="image/jpeg",
            caption=caption,
        )
    except Exception:
        await update.message.reply_text(  # type: ignore[union-attr]
            "⚠️ Sorry, I couldn't analyse that image. Please try again."
        )
        return

    # Persist memory
    user_content = f"[Sent a photo]{f': {caption}' if caption else ''}"
    await memory.append_messages(
        user_id,
        [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": reply},
        ],
    )

    await _safe_reply(update, reply)


# ── Voice Handler (Transcription + Response) ──────────────────────────────────


@authorized_only
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download voice/audio message, send to Gemini for transcription + reply."""
    user_id = update.effective_user.id  # type: ignore[union-attr]

    logger.info("Voice message from user %s", user_id)
    await _send_typing(update)

    # Get the voice or audio object
    voice = update.message.voice or update.message.audio  # type: ignore[union-attr]
    if not voice:
        return

    file = await voice.get_file()
    audio_bytes = await file.download_as_bytearray()

    # Determine MIME type
    mime_type = voice.mime_type or "audio/ogg"

    # Load history for context
    history = await memory.get_history(user_id)

    try:
        reply = await ai_client.get_audio_response(
            history,
            audio_bytes=bytes(audio_bytes),
            mime_type=mime_type,
        )
    except Exception:
        await update.message.reply_text(  # type: ignore[union-attr]
            "⚠️ Sorry, I couldn't process that voice message. Please try again."
        )
        return

    # Persist memory
    await memory.append_messages(
        user_id,
        [
            {"role": "user", "content": "[Sent a voice message]"},
            {"role": "assistant", "content": reply},
        ],
    )

    await _safe_reply(update, reply)


# ── Document Handler (PDF Analysis) ──────────────────────────────────────────


@authorized_only
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download a PDF, extract text, and send to Gemini for analysis."""
    from app import doc_reader

    user_id = update.effective_user.id  # type: ignore[union-attr]
    doc = update.message.document  # type: ignore[union-attr]
    caption = update.message.caption or None  # type: ignore[union-attr]

    if not doc:
        return

    file_name = doc.file_name or "document"
    logger.info("Document from user %s: %s", user_id, file_name)
    await _send_typing(update)

    # Download file
    file = await doc.get_file()
    file_bytes = await file.download_as_bytearray()

    # Extract text
    extracted_text = doc_reader.extract_pdf_text(bytes(file_bytes))

    if not extracted_text or extracted_text.startswith("Could not extract"):
        await update.message.reply_text(  # type: ignore[union-attr]
            "⚠️ I couldn't extract any text from this PDF. "
            "It might be image-based or encrypted."
        )
        return

    # Build the prompt
    history = await memory.get_history(user_id)

    prompt = (
        f"The user sent a PDF document named \"{file_name}\"."
    )
    if caption:
        prompt += f"\nThe user's question/request: {caption}"
    else:
        prompt += "\nPlease provide a comprehensive summary and key takeaways."

    prompt += f"\n\nExtracted document text:\n\n{extracted_text}"

    user_msg = {"role": "user", "content": prompt}
    history.append(user_msg)

    try:
        reply = await ai_client.get_ai_response(history)
    except Exception:
        await update.message.reply_text(  # type: ignore[union-attr]
            "⚠️ I extracted the text but failed to analyse it. Please try again."
        )
        return

    # Persist memory
    display_msg = {"role": "user", "content": f"[Sent PDF: {file_name}]{f' — {caption}' if caption else ''}"}
    await memory.append_messages(
        user_id,
        [display_msg, {"role": "assistant", "content": reply}],
    )

    await _safe_reply(update, reply)


# ── Text Message Handler (with URL detection) ────────────────────────────────


@authorized_only
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Main handler: receives a user message, queries Gemini, and replies.
    Now also detects URLs and offers to summarise linked pages.

    Flow:
      1. Load user's history from the database.
      2. Check if message contains URLs — if so, extract & summarise.
      3. Append the new user message.
      4. Send full history to Gemini.
      5. Append Gemini's reply.
      6. Persist updated history.
      7. Send reply to Telegram.
    """
    from app import url_summarizer

    user_id = update.effective_user.id  # type: ignore[union-attr]
    user_text = update.message.text  # type: ignore[union-attr]

    if not user_text:
        return  # ignore non-text messages (stickers, photos, etc.)

    logger.info("Message from user %s: %.80s", user_id, user_text)

    # Show typing indicator while we fetch the response
    await _send_typing(update)

    # 1. Load existing history
    history = await memory.get_history(user_id)

    # 2. Check for URLs — extract content if found
    urls = url_summarizer.find_urls(user_text)
    extra_context = ""

    if urls:
        for url in urls[:2]:  # Limit to 2 URLs max
            logger.info("Extracting content from URL: %s", url)
            content = await url_summarizer.extract_url_content(url)
            if content and not content.startswith("Failed") and not content.startswith("Cannot"):
                extra_context += f"\n\n---\n📄 Content from {url}:\n{content}\n---"

    # 3. Build the user message
    if extra_context:
        enriched_text = (
            f"{user_text}\n\n"
            f"[The following web page content was automatically extracted for context. "
            f"Use it to help answer the user's request.]{extra_context}"
        )
        user_msg = {"role": "user", "content": enriched_text}
    else:
        user_msg = {"role": "user", "content": user_text}

    history.append(user_msg)

    try:
        # 4. Get Gemini's response
        reply = await ai_client.get_ai_response(history)
    except Exception:
        # Surface a friendly error without leaking internals
        await update.message.reply_text(  # type: ignore[union-attr]
            "⚠️ Sorry, I ran into an issue reaching my AI backend. "
            "Please try again in a moment."
        )
        return

    # 5 & 6. Persist both turns together (store original text, not enriched)
    await memory.append_messages(
        user_id,
        [{"role": "user", "content": user_text}, {"role": "assistant", "content": reply}],
    )

    # 7. Reply
    await _safe_reply(update, reply)


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
    app.add_handler(CommandHandler("search", cmd_search))

    # Register media handlers (order matters — more specific first)
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_document))

    # Register text message handler (catch-all for text, must be last)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Register global error handler
    app.add_error_handler(error_handler)

    logger.info("Application built — handlers registered.")
    return app
