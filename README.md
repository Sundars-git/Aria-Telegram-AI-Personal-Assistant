# 🤖 Nila — Autonomous AI Executive Assistant for Telegram

A personal AI-powered Telegram bot built with [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) and [Google Gemini](https://ai.google.dev/). Nila is a fully autonomous executive assistant that can chat, search the web, analyse images, transcribe voice messages, read PDFs, manage your Gmail, control your Google Calendar, remember things long-term, and set reminders — all through a single Telegram conversation.

## ✨ Features

### 💬 AI Chat & Analysis
- **Conversational AI** — Powered by Google Gemini 2.5 Flash with persistent per-user memory
- **Image Analysis** — Send a photo and Nila describes & analyses it using Gemini Vision
- **Voice Messages** — Send a voice note and Nila transcribes it, then responds to the content
- **PDF Analysis** — Send a PDF document and Nila extracts the text and summarises it

### 🔍 Web Intelligence
- **Web Search** — Use `/search <query>` or just ask — Nila searches DuckDuckGo and summarises results
- **URL Summarisation** — Send a URL and Nila fetches the page and summarises it

### 🧠 Memory & Reminders
- **Long-Term Memory** — Tell Nila to remember facts, preferences, deadlines, contacts — persisted across sessions in SQLite
- **Timed Reminders** — Ask Nila to remind you about anything — fires a Telegram message when the time is up

### 📧 Gmail Integration
- **Read Emails** — Ask Nila to check your inbox, show unread emails, or search by sender/subject
- **Draft Replies** — Nila creates draft replies in Gmail (never auto-sends — safety first)

### 📅 Google Calendar Integration
- **Check Availability** — Ask what's on your calendar for any date
- **List Upcoming Events** — See your next appointments at a glance
- **Create Events** — Schedule meetings and appointments by just asking

### 🤖 Autonomous Tool Calling
Nila uses **Gemini Function Calling** to autonomously decide when to use tools. You don't need special commands — just talk naturally:
- *"What's the latest AI news?"* → automatically searches the web
- *"Remember my birthday is March 15"* → automatically stores in memory
- *"Remind me to call Mom in 30 minutes"* → automatically sets a reminder
- *"Check my email"* → automatically reads Gmail
- *"Am I free tomorrow at 3pm?"* → automatically checks Calendar

### 🔒 Security & Access Control
- **User Authorization** — Restrict access to specific Telegram user IDs
- **Gmail Safety** — Email replies are saved as drafts only, never sent automatically
- **OAuth2** — Google API access uses secure OAuth2 with token refresh

## 📁 Project Structure

```
├── main.py                  # Entry point — polling/webhook switching
├── render.yaml              # Render deployment blueprint
├── requirements.txt         # Python dependencies
├── credentials.json         # Google OAuth2 credentials (gitignored)
├── token.json               # Google OAuth2 token (gitignored)
├── .env.example             # Environment variable template
└── app/
    ├── __init__.py
    ├── bot.py               # Telegram handlers (commands + media + messages)
    ├── ai_client.py         # Gemini API wrapper (text, vision, audio, tools)
    ├── tools.py             # Tool registry & dispatcher (9 tools)
    ├── config.py            # Environment loader & system prompt
    ├── memory.py            # SQLite conversation history + long-term memory
    ├── reminders.py         # Timed reminders (JobQueue + SQLite)
    ├── google_auth.py       # Google OAuth2 credential management
    ├── gmail_client.py      # Gmail API (read, draft reply)
    ├── calendar_client.py   # Calendar API (check, list, create)
    ├── web_search.py        # DuckDuckGo web search
    ├── url_summarizer.py    # URL content extraction & summarisation
    └── doc_reader.py        # PDF text extraction
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- A [Telegram Bot Token](https://t.me/BotFather)
- A [Google Gemini API Key](https://aistudio.google.com/apikey)
- *(Optional)* Google Cloud project for Gmail & Calendar

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

### Gmail & Calendar Setup (Optional)

1. Create a project at [console.cloud.google.com](https://console.cloud.google.com)
2. Enable **Gmail API** and **Google Calendar API**
3. Configure **OAuth consent screen** → add yourself as a test user
4. Create **OAuth2 credentials** (Desktop App) → download as `credentials.json`
5. Place `credentials.json` in the project root
6. Run: `python -m app.google_auth` → authorize in browser → `token.json` is saved

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

## 🤖 Bot Commands

| Command   | Description                                      |
|-----------|--------------------------------------------------|
| `/start`  | Welcome message with feature overview            |
| `/help`   | Show all commands and supported media types       |
| `/reset`  | Clear your conversation history                  |
| `/search` | Search the web (e.g. `/search latest AI news`)   |

### Supported Interactions

| Input Type          | What Nila Does                                         |
|---------------------|--------------------------------------------------------|
| 📷 Photos          | Analyses the image; add a caption to ask a question     |
| 🎙️ Voice/Audio    | Transcribes the message and responds to the content    |
| 📄 PDF Files       | Extracts text and provides summary or answers questions |
| 🔗 URLs in text    | Fetches the page and summarises the content            |
| 🧠 "Remember..."  | Stores facts in long-term memory                       |
| ⏰ "Remind me..."  | Sets a timed reminder                                  |
| 📧 "Check email"   | Reads Gmail inbox                                      |
| 📅 "My schedule"   | Checks Google Calendar                                 |

## ⚙️ Configuration

All config is via environment variables (`.env` file):

| Variable                  | Required | Default            | Description                              |
|---------------------------|----------|--------------------|------------------------------------------|
| `TELEGRAM_BOT_TOKEN`      | ✅       | —                  | Bot token from @BotFather                |
| `GEMINI_API_KEY`          | ✅       | —                  | Google Gemini API key                    |
| `GEMINI_MODEL`            | ❌       | `gemini-2.0-flash` | Gemini model to use                      |
| `ALLOWED_USER_IDS`        | ❌       | *(open mode)*      | Comma-separated Telegram user IDs        |
| `DB_PATH`                 | ❌       | `memory.db`        | SQLite database path                     |
| `MAX_HISTORY`             | ❌       | `15`               | Max messages to keep per user            |
| `GOOGLE_CREDENTIALS_PATH` | ❌       | `credentials.json` | Path to Google OAuth2 credentials        |
| `GOOGLE_TOKEN_PATH`       | ❌       | `token.json`       | Path to Google OAuth2 token              |

## 🧰 Dependencies

| Package                    | Purpose                              |
|----------------------------|--------------------------------------|
| `python-telegram-bot`      | Telegram Bot API framework           |
| `httpx`                    | Async HTTP client (Gemini API)       |
| `aiosqlite`                | Async SQLite for memory & reminders  |
| `duckduckgo_search`        | Web search (no API key needed)       |
| `beautifulsoup4`           | HTML parsing for URL extraction      |
| `PyPDF2`                   | PDF text extraction                  |
| `python-dotenv`            | Environment variable loading         |
| `google-api-python-client` | Google APIs (Gmail, Calendar)        |
| `google-auth-oauthlib`     | Google OAuth2 authentication         |

## 📄 License

MIT
