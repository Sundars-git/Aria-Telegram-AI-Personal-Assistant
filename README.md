# 🤖 Aria — Telegram AI Personal Assistant

A production-ready personal AI assistant bot built with **Python**, **python-telegram-bot**, and **Ollama** (local LLM). Supports **text conversations** and **image recognition**. Runs entirely on your machine — **no API costs, no cloud dependency**.

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
| 🧠 **Local AI** | Powered by Ollama — use Llama 3.2, Mistral, Gemma, or any model |
| 📷 **Image Recognition** | Send photos and get AI-powered analysis via vision models (LLaVA) |
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
    ├── bot.py               # Telegram handlers, auth & photo support
    ├── ai_client.py         # Async Ollama API wrapper (text + vision)
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
git clone https://github.com/Sundars-git/TELEGRAM-BOT.git
cd TELEGRAM-BOT
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

### 3. Pull AI models

```bash
# Text model
ollama pull llama3.2

# Vision model (for image recognition)
ollama pull llava
```

### 4. Configure environment

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```env
TELEGRAM_BOT_TOKEN=your-bot-token-from-botfather
OLLAMA_MODEL=llama3.2
OLLAMA_VISION_MODEL=llava
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
| *(send a photo)* | Analyze an image with the vision model |

---

## 📷 Image Recognition

Send any photo to the bot and it will analyze it using the **LLaVA** vision model:

- **Without caption** → The bot describes the image in detail
- **With caption** → The bot answers your question about the image (e.g. *"What breed is this dog?"*)

The vision model automatically activates when a photo is detected — no commands needed.

---

## 🔒 Authorization

Set `ALLOWED_USER_IDS` in your `.env`:

```env
# Single user
ALLOWED_USER_IDS=123456789

# Multiple users (comma-separated)
ALLOWED_USER_IDS=123456789,987654321
```

Leave **empty** to allow everyone (open mode). Unauthorized users receive: **⛔ Access denied**.

---

## 💾 Memory System

- SQLite database (`memory.db`) — persists across restarts
- Per-user history, capped at `MAX_HISTORY` (default: 15 messages)
- Auto-prunes old messages beyond the limit
- Use `/reset` to clear your history

---

## ⚙️ Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | — | Bot token from @BotFather |
| `OLLAMA_BASE_URL` | ❌ | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | ❌ | `llama3.2` | Text model |
| `OLLAMA_VISION_MODEL` | ❌ | `llava` | Vision model for image analysis |
| `ALLOWED_USER_IDS` | ❌ | *(empty = open)* | Allowed Telegram user IDs |
| `DB_PATH` | ❌ | `memory.db` | SQLite database path |
| `MAX_HISTORY` | ❌ | `15` | Max messages per user |

---

## 🧠 Changing AI Models

### Text Models
```bash
ollama pull mistral       # Fast, strong reasoning
ollama pull gemma2        # Google's efficient model
ollama pull phi3          # Microsoft's compact model
ollama pull llama3.1      # More capable, longer context
ollama pull codellama     # Code-focused tasks
```

### Vision Models
```bash
ollama pull llava         # LLaVA 1.6 — best general vision
ollama pull llava:13b     # Larger, more accurate
ollama pull bakllava      # BakLLaVA — alternative vision model
```

Update `OLLAMA_MODEL` or `OLLAMA_VISION_MODEL` in `.env` and restart the bot.

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
