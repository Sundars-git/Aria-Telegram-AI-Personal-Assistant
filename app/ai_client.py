"""
ai_client.py — Thin async wrapper around the Ollama local LLM API.

Responsibilities:
  - Accept a conversation history (list of role/content dicts).
  - Support optional image inputs (base64-encoded) for vision models.
  - Prepend the system prompt.
  - Call Ollama's /api/chat endpoint and return the assistant's reply.
  - Surface clean, loggable errors to the caller.
"""

import logging
from typing import List, Dict, Optional

import httpx

from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_VISION_MODEL, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Reusable async HTTP client — keeps connection pool alive across requests.
_http_client = httpx.AsyncClient(timeout=180.0)


async def get_ai_response(
    history: List[Dict[str, str]],
    image_b64: Optional[str] = None,
) -> str:
    """
    Send the full conversation history to Ollama and return its response.

    Args:
        history: List of {"role": "user"|"assistant", "content": "..."} dicts.
                 This should already include the latest user message at the end.
        image_b64: Optional base64-encoded image string. When provided, the
                   vision model is used and the image is attached to the last
                   user message.

    Returns:
        The assistant's reply text.

    Raises:
        httpx.HTTPStatusError on API-level failures (caller should catch).
    """
    # Choose model based on whether an image is present
    model = OLLAMA_VISION_MODEL if image_b64 else OLLAMA_MODEL

    # Build messages list with system prompt
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for msg in history:
        entry = {"role": msg["role"], "content": msg["content"]}
        messages.append(entry)

    # Attach image to the last user message if provided
    if image_b64 and messages:
        for i in range(len(messages) - 1, -1, -1):
            if messages[i]["role"] == "user":
                messages[i]["images"] = [image_b64]
                break

    try:
        response = await _http_client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
            },
        )
        response.raise_for_status()

        data = response.json()
        reply: str = data["message"]["content"]
        logger.debug("Ollama responded (%d chars) using model '%s'.", len(reply), model)
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
