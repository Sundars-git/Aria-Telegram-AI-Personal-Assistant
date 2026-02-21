# 🤖 Aria — Telegram AI Personal Assistant

A production-ready personal AI assistant bot built with **Python**, **python-telegram-bot**, and **Ollama** (local LLM). Runs entirely on your machine — **no API costs, no cloud dependency**.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot%20API-26A5E4?logo=telegram&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-000000?logo=ollama&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Memory-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧠 **Local AI** | Powered by Ollama — use Llama 3.2, Mistral, Gemma, or any model you want |
| 🔒 **Access Control** | Restrict bot usage to specific Telegram user IDs |
| 💾 **Persistent Memory** | SQLite-backed conversation history that survives restarts |
| ⚡ **Async** | Fully asynchronous — handles multiple users without blocking |
| 🆓 **100% Free** | No API keys, no subscriptions, no cloud costs |

---

## 📁 Project Structure

```
clawd/
├── .env                    # Your configuration (secrets — never commit!)
├── .env.example            # Template for .env
├── main.py                 # Entry point — starts the bot
├── requirements.txt        # Python dependencies
├── README.md
└── app/
    ├── __init__.py          # Package marker
    ├── config.py            # Environment variable loading & validation
    ├── bot.py               # Telegram handlers & authorization
    ├── ai_client.py         # Async Ollama API wrapper
    └── memory.py            # SQLite conversation memory
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** — [python.org/downloads](https://www.python.org/downloads/)
- **Ollama** — [ollama.com/download](https://ollama.com/download)
- **Telegram Bot Token** — talk to [@BotFather](https://t.me/BotFather) on Telegram → `/newbot`

### 1. Clone the repository

```bash
git clone https://github.com/Sundars-git/Telegram-clawdbot.git
cd Telegram-clawdbot
```

### 2. Set up Python environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Pull an AI model

```bash
ollama pull llama3.2
```

> 💡 You can use any Ollama model: `mistral`, `gemma2`, `phi3`, `llama3.1`, `codellama`, etc.

### 4. Configure environment

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```env
TELEGRAM_BOT_TOKEN=your-bot-token-from-botfather
OLLAMA_MODEL=llama3.2
ALLOWED_USER_IDS=your-telegram-user-id
```

> 🔑 **How to find your Telegram User ID:** Message [@userinfobot](https://t.me/userinfobot) on Telegram — it replies with your numeric ID.

### 5. Run the bot

```bash
# Make sure Ollama is running
ollama serve

# Start the bot
python main.py
```

You should see:
```
2026-02-21 10:00:00 | INFO | __main__ — Starting Telegram AI Assistant…
2026-02-21 10:00:01 | INFO | app.memory — Database initialised at 'memory.db'.
2026-02-21 10:00:01 | INFO | telegram.ext.Application — Application started
```

Open Telegram, find your bot, and send `/start` 🎉

---

## 🎮 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | List all available commands |
| `/reset` | Clear your conversation history |
| *(any text)* | Chat with the AI |

---

## 🔒 Authorization

The bot restricts access to approved users only. Set `ALLOWED_USER_IDS` in your `.env`:

```env
# Single user
ALLOWED_USER_IDS=123456789

# Multiple users (comma-separated)
ALLOWED_USER_IDS=123456789,987654321,555555555
```

Leave it **empty** to allow everyone (open mode — not recommended for production).

Unauthorized users receive: **⛔ Access denied — you are not authorized to use this bot.**

---

## 💾 Memory System

Conversations are stored in a local **SQLite database** (`memory.db`):

- Each user gets their own conversation history
- History is capped at `MAX_HISTORY` messages (default: 15) to control context size
- Old messages are automatically pruned
- Memory persists across bot restarts
- Use `/reset` to clear your history

---

## ⚙️ Configuration

All settings are managed via environment variables in `.env`:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | — | Bot token from @BotFather |
| `OLLAMA_BASE_URL` | ❌ | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | ❌ | `llama3.2` | Model to use for responses |
| `ALLOWED_USER_IDS` | ❌ | *(empty = open)* | Comma-separated allowed Telegram user IDs |
| `DB_PATH` | ❌ | `memory.db` | Path to SQLite database |
| `MAX_HISTORY` | ❌ | `15` | Max messages per user in memory |

---

## 🧠 Changing the AI Model

Swap models anytime by changing `OLLAMA_MODEL` in `.env`:

```bash
# Pull a different model
ollama pull mistral
ollama pull gemma2
ollama pull phi3
ollama pull codellama
```

```env
OLLAMA_MODEL=mistral
```

Restart the bot to apply. Popular models:

| Model | Size | Best For |
|-------|------|----------|
| `llama3.2` | 2 GB | General purpose, balanced |
| `llama3.1` | 4.7 GB | More capable, longer context |
| `mistral` | 4.1 GB | Fast, strong reasoning |
| `gemma2` | 5.4 GB | Google's efficient model |
| `phi3` | 2.2 GB | Microsoft's compact model |
| `codellama` | 3.8 GB | Code-focused tasks |

---

## 🌐 Deploying to a Server

### Render

1. Push code to GitHub (make sure `.env` is in `.gitignore`)
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect your GitHub repo
4. Set:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
5. Add environment variables under **Environment**
6. Click **Create Web Service**

> ⚠️ You'll need Ollama running on the server or use a remote Ollama instance by setting `OLLAMA_BASE_URL`.

### Railway

1. Push code to GitHub
2. Go to [railway.app](https://railway.app) → **New Project → Deploy from GitHub**
3. Set start command: `python main.py`
4. Add environment variables
5. Deploy

---

## 🛠️ Customization

| What to change | Where |
|----------------|-------|
| Bot personality / system prompt | `app/config.py` → `SYSTEM_PROMPT` |
| AI model | `.env` → `OLLAMA_MODEL` |
| Message history limit | `.env` → `MAX_HISTORY` |
| Add new commands | `app/bot.py` |
| Modify memory behavior | `app/memory.py` |
| Change response timeout | `app/ai_client.py` → `timeout` |

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

<div align="center">

**Made with ❤️ by [Sundars-git](https://github.com/Sundars-git)**

</div>
