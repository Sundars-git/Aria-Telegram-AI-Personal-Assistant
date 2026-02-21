"""
config.py — Loads and validates environment variables.
All sensitive credentials are read from a .env file via python-dotenv.
"""

import os
from dotenv import load_dotenv

# Load .env file into the environment
load_dotenv()


def _require(key: str) -> str:
    """Fetch a required env variable or raise a clear error."""
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Missing required environment variable: '{key}'. "
            f"Please set it in your .env file."
        )
    return value


# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")

# ── Ollama (local LLM) ───────────────────────────────────────────────────────
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")

# ── Authorization ─────────────────────────────────────────────────────────────
# Comma-separated Telegram user IDs that are allowed to use the bot.
# Leave empty to allow everyone (open mode).
_raw_ids = os.getenv("ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS: set[int] = {
    int(uid.strip()) for uid in _raw_ids.split(",") if uid.strip()
}

# ── Memory ────────────────────────────────────────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", "memory.db")
MAX_HISTORY: int = int(os.getenv("MAX_HISTORY", "15"))   # messages per user

# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT: str = """You are Aria, a sharp and dependable personal AI assistant.

Your core traits:
- Professional yet warm — you treat every user like a trusted colleague.
- Concise by default — give crisp, actionable answers unless depth is requested.
- Proactive — when a task is ambiguous, ask one clarifying question rather than guessing.
- Honest — if you don't know something, say so; never fabricate facts.

Your capabilities:
- Task & project management: help break down goals, prioritise work, draft plans.
- Research & summarisation: condense long content into clear takeaways.
- Writing & editing: draft emails, reports, messages, and improve existing text.
- Brainstorming: generate creative ideas and explore options.
- General Q&A: answer factual, technical, or practical questions accurately.

Formatting rules:
- Use Markdown only when it genuinely aids readability (lists, code blocks, bold key terms).
- Keep responses under ~200 words unless the user explicitly asks for more detail.
- Never pad responses with filler phrases like "Certainly!" or "Great question!".

You remember the conversation history within this session and use it for context.
Always stay on-topic and focused on helping the user accomplish their goals.
"""
