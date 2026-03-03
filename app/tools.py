"""
tools.py — Tool registry and dispatcher for Nila's autonomous capabilities.

Defines the tool schemas for Gemini function calling and routes
tool execution to the appropriate module.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


# ── Tool Definitions (Gemini Function Calling format) ─────────────────────────

TOOL_DECLARATIONS = [
    {
        "name": "web_search",
        "description": (
            "Search the web for current information using DuckDuckGo. "
            "Use when the user asks about recent events, needs factual info "
            "you're unsure about, or explicitly requests a search."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "The search query string",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "url_summarize",
        "description": (
            "Fetch and extract readable text from a web URL. "
            "Use when the user sends a link or asks to summarize a webpage."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "url": {
                    "type": "STRING",
                    "description": "The full URL to fetch and extract text from",
                }
            },
            "required": ["url"],
        },
    },
    {
        "name": "memory_store",
        "description": (
            "Store important long-term information about the user. "
            "Use when the user shares preferences, important dates, contacts, "
            "deadlines, or any facts they want remembered across sessions."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "key": {
                    "type": "STRING",
                    "description": (
                        "A short descriptive key, e.g. 'favorite_color', "
                        "'birthday', 'boss_name', 'project_deadline'"
                    ),
                },
                "value": {
                    "type": "STRING",
                    "description": "The information to store",
                },
            },
            "required": ["key", "value"],
        },
    },
    {
        "name": "memory_retrieve",
        "description": (
            "Retrieve stored long-term information about the user. "
            "Use when the user asks about something previously stored, "
            "or to recall preferences/context. Use key='all' to list everything."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "key": {
                    "type": "STRING",
                    "description": (
                        "The memory key to look up, or 'all' to list "
                        "all stored memories"
                    ),
                }
            },
            "required": ["key"],
        },
    },
    {
        "name": "set_reminder",
        "description": (
            "Set a timed reminder. The bot will send the user a Telegram "
            "message after the specified number of minutes. "
            "Use for any 'remind me' or 'alert me' requests."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "text": {
                    "type": "STRING",
                    "description": "The reminder message to send",
                },
                "delay_minutes": {
                    "type": "NUMBER",
                    "description": "Number of minutes from now to fire the reminder",
                },
            },
            "required": ["text", "delay_minutes"],
        },
    },
    {
        "name": "gmail_read",
        "description": (
            "Read recent or filtered emails from the user's Gmail inbox. "
            "Use when the user asks to check email, see unread messages, or "
            "search for specific emails. Supports Gmail search queries."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": (
                        "Gmail search query, e.g. 'is:unread', "
                        "'from:boss@company.com', 'subject:invoice'. "
                        "Leave empty for recent inbox emails."
                    ),
                },
                "max_results": {
                    "type": "NUMBER",
                    "description": "Number of emails to return (default 5, max 10)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "gmail_draft_reply",
        "description": (
            "Create a draft reply to an email. NEVER sends the email — "
            "only saves it as a draft in Gmail for the user to review. "
            "Use when the user asks to reply to an email."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "message_id": {
                    "type": "STRING",
                    "description": "The Gmail message ID to reply to",
                },
                "reply_body": {
                    "type": "STRING",
                    "description": "The text content of the reply",
                },
            },
            "required": ["message_id", "reply_body"],
        },
    },
    {
        "name": "calendar_check",
        "description": (
            "Check Google Calendar availability or list upcoming events. "
            "Use when the user asks about their schedule, availability, "
            "or what's on their calendar."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date": {
                    "type": "STRING",
                    "description": (
                        "Date to check in YYYY-MM-DD format. "
                        "Use 'upcoming' to list next upcoming events."
                    ),
                },
                "time_start": {
                    "type": "STRING",
                    "description": "Optional start time in HH:MM format (24h)",
                },
                "time_end": {
                    "type": "STRING",
                    "description": "Optional end time in HH:MM format (24h)",
                },
            },
            "required": ["date"],
        },
    },
    {
        "name": "calendar_create_event",
        "description": (
            "Create a new Google Calendar event. Use when the user asks "
            "to schedule a meeting, appointment, or event."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Event title/name",
                },
                "start_time": {
                    "type": "STRING",
                    "description": (
                        "Start time in ISO 8601 format, "
                        "e.g. '2026-03-05T14:00:00'"
                    ),
                },
                "end_time": {
                    "type": "STRING",
                    "description": (
                        "End time in ISO 8601 format, "
                        "e.g. '2026-03-05T15:00:00'"
                    ),
                },
                "description": {
                    "type": "STRING",
                    "description": "Optional event description or notes",
                },
            },
            "required": ["title", "start_time", "end_time"],
        },
    },
]


# ── Tool Executor ─────────────────────────────────────────────────────────────


async def execute_tool(
    name: str,
    args: Dict[str, Any],
    context: Dict[str, Any],
) -> str:
    """
    Execute a tool by name and return the result as a string.

    Args:
        name:    The tool function name from Gemini's functionCall.
        args:    The arguments dict from Gemini's functionCall.
        context: Execution context containing:
                   - user_id:     Telegram user ID
                   - chat_id:     Telegram chat ID
                   - bot_context: python-telegram-bot ContextTypes (for JobQueue)

    Returns:
        A string result to feed back to Gemini as a functionResponse.
    """
    user_id = context.get("user_id")

    try:
        # ── Web search ────────────────────────────────────────────────────
        if name == "web_search":
            from app import web_search

            query = args.get("query", "")
            logger.info("🔧 Tool: web_search(%s)", query)
            return await web_search.search(query)

        # ── URL summarization ─────────────────────────────────────────────
        elif name == "url_summarize":
            from app import url_summarizer

            url = args.get("url", "")
            logger.info("🔧 Tool: url_summarize(%s)", url)
            return await url_summarizer.extract_url_content(url)

        # ── Long-term memory: store ───────────────────────────────────────
        elif name == "memory_store":
            from app import memory

            key = args.get("key", "")
            value = args.get("value", "")
            logger.info("🔧 Tool: memory_store(%s, %s)", key, value[:50])
            await memory.store_long_term(user_id, key, value)
            return f"Stored: {key} = {value}"

        # ── Long-term memory: retrieve ────────────────────────────────────
        elif name == "memory_retrieve":
            from app import memory

            key = args.get("key", "")
            logger.info("🔧 Tool: memory_retrieve(%s)", key)

            if key.lower() == "all":
                memories = await memory.list_long_term(user_id)
                if not memories:
                    return "No memories stored yet for this user."
                return "\n".join(f"• {k}: {v}" for k, v in memories)
            else:
                value = await memory.retrieve_long_term(user_id, key)
                return value if value else f"No memory found for key '{key}'."

        # ── Set reminder ──────────────────────────────────────────────────
        elif name == "set_reminder":
            from app import reminders

            text = args.get("text", "Reminder!")
            delay = float(args.get("delay_minutes", 1))
            chat_id = context.get("chat_id")
            bot_context = context.get("bot_context")

            logger.info("🔧 Tool: set_reminder(%s, %.1f min)", text[:30], delay)
            await reminders.schedule_reminder(
                user_id=user_id,
                chat_id=chat_id,
                text=text,
                delay_minutes=delay,
                bot_context=bot_context,
            )
            return f"Reminder set: '{text}' — will fire in {delay} minute(s)."

        # ── Gmail: read emails ────────────────────────────────────────────
        elif name == "gmail_read":
            from app import gmail_client

            query = args.get("query", None)
            max_results = int(args.get("max_results", 5))
            logger.info("🔧 Tool: gmail_read(query=%s, max=%d)", query, max_results)
            return await gmail_client.read_emails(query=query, max_results=max_results)

        # ── Gmail: draft reply ────────────────────────────────────────────
        elif name == "gmail_draft_reply":
            from app import gmail_client

            message_id = args.get("message_id", "")
            reply_body = args.get("reply_body", "")
            logger.info("🔧 Tool: gmail_draft_reply(%s)", message_id)
            return await gmail_client.draft_reply(
                message_id=message_id,
                reply_body=reply_body,
            )

        # ── Calendar: check availability ──────────────────────────────────
        elif name == "calendar_check":
            from app import calendar_client

            date = args.get("date", "")
            logger.info("🔧 Tool: calendar_check(%s)", date)

            if date.lower() == "upcoming":
                return await calendar_client.list_upcoming(count=5)
            else:
                return await calendar_client.check_availability(
                    date=date,
                    time_start=args.get("time_start"),
                    time_end=args.get("time_end"),
                )

        # ── Calendar: create event ────────────────────────────────────────
        elif name == "calendar_create_event":
            from app import calendar_client

            logger.info("🔧 Tool: calendar_create_event(%s)", args.get("title"))
            return await calendar_client.create_event(
                title=args.get("title", "New Event"),
                start_time=args.get("start_time", ""),
                end_time=args.get("end_time", ""),
                description=args.get("description"),
            )

        # ── Unknown tool ──────────────────────────────────────────────────
        else:
            logger.warning("Unknown tool requested: %s", name)
            return f"Error: Unknown tool '{name}'."

    except Exception as exc:
        logger.exception("Tool execution failed: %s(%s)", name, args)
        return f"Tool error: {exc}"
