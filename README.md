# 🤖 Aria — Telegram AI Assistant

A personal AI-powered Telegram bot built with [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) and [Google Gemini](https://ai.google.dev/). Aria can chat, analyse images, transcribe voice messages, read PDFs, search the web, and summarise URLs — all through Telegram.

## ✨ Features

- **💬 Conversational AI** — Powered by Google Gemini (2.5 Flash by default) with persistent per-user memory
- **🖼️ Image Analysis** — Send a photo and Aria describes & analyses it using Gemini Vision
- **🎙️ Voice Messages** — Send a voice note and Aria transcribes it, then responds to the content
- **📄 PDF Analysis** — Send a PDF document and Aria extracts the text and summarises it
- **🔍 Web Search** — Use `/search <query>` to search the web via DuckDuckGo — results are summarised by Gemini
- **🔗 URL Summarisation** — Send a URL in any message and Aria fetches the page and summarises it
- **🔒 User Authorization** — Restrict access to specific Telegram user IDs
- **☁️ Dual Deploy Mode** — Polling for local dev, webhooks for cloud (auto-detected)
- **🚀 One-Click Deploy** — Render blueprint included (`render.yaml`)

## 📁 Project Structure

```
├── main.py              # Entry point — handles polling/webhook switching
├── render.yaml          # Render deployment blueprint
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
└── app/
    ├── __init__.py
    ├── bot.py           # Telegram handlers (commands + media + messages)
    ├── ai_client.py     # Async Gemini API wrapper (text, vision, audio)
    ├── config.py        # Environment variable loader & system prompt
    ├── memory.py        # SQLite-backed conversation history
    ├── web_search.py    # DuckDuckGo web search skill
    ├── url_summarizer.py # URL content extraction & summarisation
    └── doc_reader.py    # PDF text extraction
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

| Command   | Description                                      |
|-----------|--------------------------------------------------|
| `/start`  | Welcome message with feature overview            |
| `/help`   | Show all commands and supported media types       |
| `/reset`  | Clear your conversation history                  |
| `/search` | Search the web (e.g. `/search latest AI news`)   |

### Supported Media

| Media Type      | What Aria Does                                         |
|-----------------|--------------------------------------------------------|
| 📷 Photos      | Analyses the image; add a caption to ask a question     |
| 🎙️ Voice/Audio | Transcribes the message and responds to the content    |
| 📄 PDF Files   | Extracts text and provides summary or answers questions |
| 🔗 URLs in text | Fetches the page and summarises the content            |

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

## 🧰 Dependencies

| Package              | Purpose                         |
|----------------------|---------------------------------|
| `python-telegram-bot`| Telegram Bot API framework      |
| `httpx`              | Async HTTP client (Gemini API)  |
| `aiosqlite`          | Async SQLite for memory         |
| `duckduckgo_search`  | Web search (no API key needed)  |
| `beautifulsoup4`     | HTML parsing for URL extraction |
| `PyPDF2`             | PDF text extraction             |
| `python-dotenv`      | Environment variable loading    |

## 📄 License

MIT
