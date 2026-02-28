# 🤖 Aria — Telegram AI Assistant

A personal AI-powered Telegram bot built with [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) and [Google Gemini](https://ai.google.dev/). Aria can help with task management, research, writing, brainstorming, and general Q&A — all through Telegram.

## ✨ Features

- **Conversational AI** — Powered by Google Gemini (2.5 Flash by default)
- **Persistent Memory** — Conversation history stored in SQLite (per-user)
- **User Authorization** — Restrict access to specific Telegram user IDs
- **Dual Deploy Mode** — Polling for local dev, webhooks for cloud (auto-detected)
- **One-Click Deploy** — Render blueprint included (`render.yaml`)

## 📁 Project Structure

```
├── main.py              # Entry point — handles polling/webhook switching
├── render.yaml          # Render deployment blueprint
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
└── app/
    ├── __init__.py
    ├── bot.py           # Telegram handlers (/start, /help, /reset, messages)
    ├── ai_client.py     # Async Gemini API wrapper
    ├── config.py        # Environment variable loader & system prompt
    └── memory.py        # SQLite-backed conversation history
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- A [Telegram Bot Token](https://t.me/BotFather)
- A [Google Gemini API Key](https://aistudio.google.com/apikey)

### Local Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/Sundars-git/TELEGRAM-BOT.git
   cd TELEGRAM-BOT
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your actual tokens
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```
   The bot starts in **polling mode** automatically for local development.

## ☁️ Deploy to Render (Free Tier)

This bot supports Render's free Web Service tier using webhook mode.

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect your GitHub repo
4. Set **Build Command**: `pip install -r requirements.txt`
5. Set **Start Command**: `python main.py`
6. Add environment variables: `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `ALLOWED_USER_IDS`
7. Deploy!

> Render automatically sets `RENDER_EXTERNAL_URL` — the bot detects this and switches to webhook mode.

> **Note:** Render's free tier spins down after 15 min of inactivity. The first message after idle may take ~30s.

## 🤖 Bot Commands

| Command  | Description                          |
|----------|--------------------------------------|
| `/start` | Welcome message                      |
| `/help`  | Show available commands              |
| `/reset` | Clear your conversation history      |

Any other text message gets a response from Aria.

## ⚙️ Configuration

All config is via environment variables (`.env` file):

| Variable             | Required | Default            | Description                              |
|----------------------|----------|--------------------|------------------------------------------|
| `TELEGRAM_BOT_TOKEN` | ✅       | —                  | Bot token from @BotFather                |
| `GEMINI_API_KEY`     | ✅       | —                  | Google Gemini API key                    |
| `GEMINI_MODEL`       | ❌       | `gemini-2.0-flash` | Gemini model to use                      |
| `ALLOWED_USER_IDS`   | ❌       | *(open mode)*      | Comma-separated Telegram user IDs        |
| `DB_PATH`            | ❌       | `memory.db`        | SQLite database path                     |
| `MAX_HISTORY`        | ❌       | `15`               | Max messages to keep per user            |

## 📄 License

MIT
