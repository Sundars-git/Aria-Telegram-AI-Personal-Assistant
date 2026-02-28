"""
main.py — Entry point for the Telegram AI Assistant.

Supports two modes:
  • Polling  — for local development (default)
  • Webhook  — for Render / cloud deployment (auto-detected via RENDER_EXTERNAL_URL)

Set RENDER_EXTERNAL_URL in environment or .env to enable webhook mode.
"""

import logging
import os
import sys

from app.bot import build_application
from app import memory


# ── Logging setup ─────────────────────────────────────────────────────────────

def configure_logging() -> None:
    """Set up root logger with a sensible format and level."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    # Quieten noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


# ── Post-init (runs before polling/webhook starts) ────────────────────────────

async def on_startup(application) -> None:
    """Initialise the SQLite database on first launch."""
    await memory.init_db()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    configure_logging()
    logger = logging.getLogger(__name__)

    application = build_application()
    application.post_init = on_startup

    # Auto-detect Render deployment
    render_url = os.getenv("RENDER_EXTERNAL_URL")

    if render_url:
        # ── Webhook mode (Render / cloud) ─────────────────────────────────────
        port = int(os.getenv("PORT", "10000"))
        webhook_url = f"{render_url}/webhook"
        logger.info("Starting in WEBHOOK mode → %s (port %d)", webhook_url, port)

        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path="/webhook",
            webhook_url=webhook_url,
            drop_pending_updates=True,
        )
    else:
        # ── Polling mode (local development) ──────────────────────────────────
        logger.info("Starting in POLLING mode (local dev)…")
        application.run_polling(
            poll_interval=1.0,
            timeout=20,
            drop_pending_updates=True,
        )


if __name__ == "__main__":
    main()
