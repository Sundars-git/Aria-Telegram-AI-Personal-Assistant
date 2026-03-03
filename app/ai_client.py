"""
ai_client.py — Async wrapper around the Google Gemini REST API.

Responsibilities:
  - Accept a conversation history (list of role/content dicts).
  - Map the system prompt and history to Gemini's format.
  - Call Gemini's generateContent endpoint and return the assistant's reply.
  - Support multimodal inputs: images (vision) and audio (voice).
  - Support autonomous tool/function calling with a dispatch loop.
  - Surface clean, loggable errors to the caller.
"""

import base64
import logging
from typing import Any, Dict, List, Optional

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

# Maximum rounds of tool calls before giving up (prevents infinite loops)
_MAX_TOOL_ROUNDS = 5


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


async def _call_gemini(payload: dict) -> dict:
    """
    Send a payload to Gemini and return the raw response JSON.
    Shared by all response functions.
    """
    url = _API_URL.format(model=GEMINI_MODEL, key=GEMINI_API_KEY)

    try:
        response = await _http_client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

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


def _extract_text(data: dict) -> str:
    """Extract the text reply from a Gemini response dict."""
    return data["candidates"][0]["content"]["parts"][0]["text"]


# ── Standard text response (no tools) ────────────────────────────────────────


async def get_ai_response(history: List[Dict[str, str]]) -> str:
    """
    Send the full conversation history to Gemini and return its response.
    This is the simple, tool-free version — used by /search and other commands.
    """
    contents = _build_gemini_contents(history)

    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
    }

    data = await _call_gemini(payload)
    reply = _extract_text(data)
    logger.debug("Gemini responded (%d chars).", len(reply))
    return reply


# ── Tool-augmented response (autonomous function calling) ─────────────────────


async def get_ai_response_with_tools(
    history: List[Dict[str, str]],
    tool_context: Dict[str, Any],
) -> str:
    """
    Send conversation to Gemini with tool definitions.
    If Gemini wants to call a tool, execute it and loop until a final
    text response is produced.

    Falls back to a plain (no-tools) response if function calling fails.
    """
    from app.tools import TOOL_DECLARATIONS, execute_tool

    contents = _build_gemini_contents(history)

    try:
        for round_num in range(_MAX_TOOL_ROUNDS):
            payload = {
                "contents": contents,
                "tools": [{"functionDeclarations": TOOL_DECLARATIONS}],
                "systemInstruction": {
                    "parts": [{"text": SYSTEM_PROMPT}]
                },
            }

            data = await _call_gemini(payload)
            candidate = data["candidates"][0]
            parts = candidate["content"]["parts"]

            # Check if Gemini wants to call a function
            if "functionCall" in parts[0]:
                fc = parts[0]["functionCall"]
                func_name = fc["name"]
                func_args = fc.get("args", {})

                logger.info(
                    "Gemini tool call (round %d): %s(%s)",
                    round_num + 1, func_name, func_args,
                )

                # Execute the tool
                result = await execute_tool(func_name, func_args, tool_context)

                # Append the model's function call to contents
                contents.append({
                    "role": "model",
                    "parts": [{"functionCall": {"name": func_name, "args": func_args}}],
                })

                # Append the function result (role MUST be "function")
                contents.append({
                    "role": "function",
                    "parts": [{
                        "functionResponse": {
                            "name": func_name,
                            "response": {"name": func_name, "content": result},
                        }
                    }],
                })

                continue  # Loop back — Gemini will process the tool result

            # It's a text response — we're done
            reply = parts[0].get("text", "")
            logger.debug(
                "Gemini final response (%d chars, %d tool round(s)).",
                len(reply), round_num,
            )
            return reply

        # Exhausted tool rounds
        logger.warning("Exhausted %d tool rounds.", _MAX_TOOL_ROUNDS)
        return (
            "I've used all available tool calls for this request. "
            "Please try rephrasing or breaking your question into smaller parts."
        )

    except Exception as exc:
        # If tool-calling fails, fall back to a plain response without tools
        logger.warning(
            "Tool-calling failed (%s), falling back to plain response.", exc,
        )
        try:
            return await get_ai_response(history)
        except Exception:
            raise  # Re-raise so the handler shows the error message



# ── Vision (image analysis) ──────────────────────────────────────────────────


async def get_vision_response(
    history: List[Dict[str, str]],
    image_bytes: bytes,
    mime_type: str,
    caption: Optional[str] = None,
) -> str:
    """
    Send an image (with optional caption) to Gemini Vision and return
    the assistant's analysis.
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

    data = await _call_gemini(payload)
    return _extract_text(data)


# ── Audio (voice transcription + response) ───────────────────────────────────


async def get_audio_response(
    history: List[Dict[str, str]],
    audio_bytes: bytes,
    mime_type: str,
) -> str:
    """
    Send an audio clip to Gemini and return a transcription + response.
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

    data = await _call_gemini(payload)
    return _extract_text(data)
