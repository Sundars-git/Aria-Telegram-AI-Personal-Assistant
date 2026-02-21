"""
ai_client.py — Thin async wrapper around the Ollama local LLM API.

Responsibilities:
  - Accept a conversation history (list of role/content dicts).
  - Prepend the system prompt.
  - Call Ollama's /api/chat endpoint and return the assistant's reply.
  - Surface clean, loggable errors to the caller.
"""

import logging
from typing import List, Dict

import httpx

from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Reusable async HTTP client — keeps connection pool alive across requests.
_http_client = httpx.AsyncClient(timeout=120.0)


async def get_ai_response(history: List[Dict[str, str]]) -> str:
    """
    Send the full conversation history to Ollama and return its response.

    Args:
        history: List of {"role": "user"|"assistant", "content": "..."} dicts.
                 This should already include the latest user message at the end.

    Returns:
        The assistant's reply text.

    Raises:
        httpx.HTTPStatusError on API-level failures (caller should catch).
    """
    # Prepend the system prompt as the first message
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    try:
        response = await _http_client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
            },
        )
        response.raise_for_status()

        data = response.json()
        reply: str = data["message"]["content"]
        logger.debug("Ollama responded (%d chars).", len(reply))
        return reply

    except httpx.ConnectError:
        logger.error(
            "Cannot connect to Ollama at %s — is it running? "
            "Start it with: ollama serve",
            OLLAMA_BASE_URL,
        )
        raise

    except httpx.HTTPStatusError as exc:
        logger.error(
            "Ollama API error %s: %s",
            exc.response.status_code,
            exc.response.text[:200],
        )
        raise

    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error calling Ollama: %s", exc)
        raise
