"""
main.py — Entry point for the Telegram AI Assistant.

Configures logging, then starts the bot in polling mode (suitable for local
development and for Render/Railway free-tier deployments where no public
HTTPS endpoint is available).

To switch to webhook mode for production, see the commented section below.
"""

import logging
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


# ── Post-init (runs before polling starts) ────────────────────────────────────

async def on_startup(application) -> None:
    """Initialise the SQLite database on first launch."""
    await memory.init_db()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    configure_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting Telegram AI Assistant…")
    application = build_application()

    # Register the startup hook to initialise the database
    application.post_init = on_startup

    # ── Polling mode (default) ────────────────────────────────────────────────
    # Ideal for development and PaaS deployments without a fixed public URL.
    application.run_polling(
        poll_interval=1.0,          # seconds between getUpdates calls
        timeout=20,                  # long-poll timeout
        drop_pending_updates=True,  # ignore messages sent while bot was offline
    )

    # ── Webhook mode (production alternative) ────────────────────────────────
    # Uncomment and set WEBHOOK_URL in your .env to use webhooks instead.
    #
    # import os
    # webhook_url = os.environ["WEBHOOK_URL"]   # e.g. https://your-app.onrender.com
    # application.run_webhook(
    #     listen="0.0.0.0",
    #     port=int(os.getenv("PORT", 8443)),
    #     webhook_url=webhook_url,
    #     drop_pending_updates=True,
    # )


if __name__ == "__main__":
    main()

