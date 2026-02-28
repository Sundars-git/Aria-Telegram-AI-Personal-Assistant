"""
ai_client.py — Thin async wrapper around the Google Gemini REST API.

Responsibilities:
  - Accept a conversation history (list of role/content dicts).
  - Map the system prompt and history to Gemini's format.
  - Call Gemini's generateContent endpoint and return the assistant's reply.
  - Surface clean, loggable errors to the caller.
"""

import logging
from typing import List, Dict

import httpx

from app.config import GEMINI_API_KEY, GEMINI_MODEL, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Gemini REST API endpoint
_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={key}"
)

# Reusable async HTTP client — keeps connection pool alive across requests.
_http_client = httpx.AsyncClient(timeout=120.0)


def _build_gemini_contents(history: List[Dict[str, str]]) -> list:
    """
    Convert our internal history format to Gemini REST API format.

    Our format:   [{"role": "user"|"assistant", "content": "..."}]
    Gemini format: [{"role": "user"|"model", "parts": [{"text": "..."}]}]
    """
    contents = []
    for msg in history:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    return contents


async def get_ai_response(history: List[Dict[str, str]]) -> str:
    """
    Send the full conversation history to Gemini and return its response.

    Args:
        history: List of {"role": "user"|"assistant", "content": "..."} dicts.
                 This should already include the latest user message at the end.

    Returns:
        The assistant's reply text.

    Raises:
        httpx.HTTPStatusError on API-level failures (caller should catch).
    """
    contents = _build_gemini_contents(history)

    url = _API_URL.format(model=GEMINI_MODEL, key=GEMINI_API_KEY)

    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
    }

    try:
        response = await _http_client.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        reply: str = data["candidates"][0]["content"]["parts"][0]["text"]
        logger.debug("Gemini responded (%d chars).", len(reply))
        return reply

    except httpx.HTTPStatusError as exc:
        logger.error(
            "Gemini API error %s: %s",
            exc.response.status_code,
            exc.response.text[:300],
        )
        raise

    except Exception as exc:
        logger.exception("Unexpected error calling Gemini: %s", exc)
        raise
