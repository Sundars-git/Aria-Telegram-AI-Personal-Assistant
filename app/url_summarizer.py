"""
url_summarizer.py — Extract readable text from a URL for summarisation.

Uses httpx (already a project dependency) + BeautifulSoup to fetch a
web page and extract its main text content.
"""

import logging
import re

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Reuse a shared async client with sensible defaults
_http_client = httpx.AsyncClient(
    timeout=30.0,
    follow_redirects=True,
    headers={
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    },
)

# Maximum characters of text to extract (keeps Gemini token usage manageable)
_MAX_TEXT_LENGTH = 6000


def _extract_text(html: str) -> str:
    """Strip HTML and return clean, readable text."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove script, style, nav, footer, header tags
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text[:_MAX_TEXT_LENGTH]


def find_urls(text: str) -> list[str]:
    """Extract all URLs from a text string."""
    url_pattern = re.compile(
        r"https?://[^\s<>\"'\]\)]+",
        re.IGNORECASE,
    )
    return url_pattern.findall(text)


async def extract_url_content(url: str) -> str:
    """
    Fetch a URL and extract its readable text content.

    Args:
        url: The web page URL to fetch.

    Returns:
        Extracted text content, or an error message if fetching fails.
    """
    try:
        response = await _http_client.get(url)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            return f"Cannot extract text from this content type: {content_type}"

        text = _extract_text(response.text)

        if not text.strip():
            return "Could not extract any readable text from this page."

        return text

    except httpx.HTTPStatusError as exc:
        logger.error("HTTP error fetching %s: %s", url, exc.response.status_code)
        return f"Failed to fetch URL (HTTP {exc.response.status_code})."

    except Exception as exc:
        logger.exception("Error fetching URL %s: %s", url, exc)
        return f"Failed to fetch URL: {exc}"
