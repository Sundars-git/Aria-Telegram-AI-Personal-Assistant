"""
ai_client.py — Thin async wrapper around the Google Gemini REST API.

Responsibilities:
  - Accept a conversation history (list of role/content dicts).
  - Map the system prompt and history to Gemini's format.
  - Call Gemini's generateContent endpoint and return the assistant's reply.
  - Support multimodal inputs: images (vision) and audio (voice).
  - Surface clean, loggable errors to the caller.
"""

import base64
import logging
from typing import List, Dict, Optional

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


async def _call_gemini(payload: dict) -> str:
    """
    Send a payload to Gemini and return the text response.
    Shared by all response functions.
    """
    url = _API_URL.format(model=GEMINI_MODEL, key=GEMINI_API_KEY)

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

    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
    }

    return await _call_gemini(payload)


async def get_vision_response(
    history: List[Dict[str, str]],
    image_bytes: bytes,
    mime_type: str,
    caption: Optional[str] = None,
) -> str:
    """
    Send an image (with optional caption) to Gemini Vision and return
    the assistant's analysis.

    Args:
        history:     Previous conversation history for context.
        image_bytes: Raw bytes of the image file.
        mime_type:   MIME type of the image (e.g. "image/jpeg").
        caption:     Optional user caption / question about the image.

    Returns:
        The assistant's reply text describing / analysing the image.
    """
    contents = _build_gemini_contents(history)

    # Build the multimodal user turn: image + optional text
    parts: list = [
        {
            "inline_data": {
                "mime_type": mime_type,
                "data": base64.b64encode(image_bytes).decode("utf-8"),
            }
        },
    ]
    if caption:
        parts.append({"text": caption})
    else:
        parts.append({"text": "Describe and analyse this image in detail."})

    contents.append({"role": "user", "parts": parts})

    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
    }

    return await _call_gemini(payload)


async def get_audio_response(
    history: List[Dict[str, str]],
    audio_bytes: bytes,
    mime_type: str,
) -> str:
    """
    Send an audio clip to Gemini and return a transcription + response.

    Args:
        history:     Previous conversation history for context.
        audio_bytes: Raw bytes of the audio file.
        mime_type:   MIME type of the audio (e.g. "audio/ogg").

    Returns:
        The assistant's reply with transcription and contextual response.
    """
    contents = _build_gemini_contents(history)

    parts: list = [
        {
            "inline_data": {
                "mime_type": mime_type,
                "data": base64.b64encode(audio_bytes).decode("utf-8"),
            }
        },
        {
            "text": (
                "This is a voice message. First, transcribe what is said. "
                "Then respond to the content of the message. "
                "Format your reply as:\n"
                "🎙️ **Transcription:**\n<transcription>\n\n"
                "💬 **Response:**\n<your response>"
            ),
        },
    ]

    contents.append({"role": "user", "parts": parts})

    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
    }

    return await _call_gemini(payload)
