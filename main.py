"""
main.py — Entry point for the Telegram AI Assistant.

Supports two modes:
  • Polling  — for local development (default)
  • Webhook  — for Render / cloud deployment (auto-detected via RENDER_EXTERNAL_URL)

Set RENDER_EXTERNAL_URL in environment or .env to enable webhook mode.
"""

import asyncio
import logging
import os
import sys

from telegram.ext import Application

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


# ── Async webhook runner (Python 3.10+ compatible) ────────────────────────────

async def run_webhook_async(application: Application, port: int, webhook_url: str) -> None:
    """
    Manually manage the application lifecycle for webhook mode.
    Uses asyncio.run() from main() so we control the event loop,
    avoiding python-telegram-bot's broken asyncio.get_event_loop().
    Includes a health-check endpoint on "/" for UptimeRobot.
    """
    from tornado.web import RequestHandler, Application as TornadoApp
    from tornado.routing import RuleRouter, Rule, PathMatches

    logger = logging.getLogger(__name__)

    # Initialize the application
    await application.initialize()

    # Run post_init if set
    if application.post_init:
        await application.post_init(application)

    # Set up the webhook
    await application.bot.set_webhook(
        url=webhook_url,
        drop_pending_updates=True,
    )

    # Start the application (handlers, job queue, etc.)
    await application.start()

    # Start the built-in webhook server
    await application.updater.start_webhook(
        listen="0.0.0.0",
        port=port,
        url_path="/webhook",
        webhook_url=webhook_url,
        drop_pending_updates=True,
    )

    # Inject a health-check route into the existing tornado server
    # so "/" returns 200 OK on the same port for UptimeRobot.
    try:
        class HealthHandler(RequestHandler):
            def get(self):
                self.set_status(200)
                self.write("Aria is alive ✓")

        httpd = application.updater.httpd
        if httpd and hasattr(httpd, '_app'):
            # Add "/" route to the existing tornado application
            existing_app = httpd._app
            if hasattr(existing_app, 'add_handlers'):
                existing_app.add_handlers(r".*", [(r"/", HealthHandler)])
                logger.info("Health-check endpoint added on /")
    except Exception as e:
        logger.warning("Could not add health-check endpoint: %s", e)

    logger.info("Webhook server running on port %d", port)

    # Keep running until interrupted
    stop_event = asyncio.Event()

    try:
        await stop_event.wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        logger.info("Shutting down…")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


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

        # Use asyncio.run() instead of application.run_webhook()
        # to avoid the "no current event loop" error on Python 3.10+.
        asyncio.run(run_webhook_async(application, port, webhook_url))
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
