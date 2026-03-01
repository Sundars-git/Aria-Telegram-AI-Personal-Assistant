"""
web_search.py — DuckDuckGo web search skill.

Provides a simple async search function that returns formatted results
for the bot to pass to Gemini for summarisation.
"""

import logging
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

# Maximum number of results to return
_MAX_RESULTS = 5


async def search(query: str) -> str:
    """
    Search the web using DuckDuckGo and return formatted results.

    Args:
        query: The search query string.

    Returns:
        A formatted string with top search results (title, snippet, URL).
        Returns an error message if the search fails.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=_MAX_RESULTS))

        if not results:
            return "No results found for that query."

        formatted = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            body = r.get("body", "No description")
            href = r.get("href", "")
            formatted.append(f"{i}. **{title}**\n   {body}\n   🔗 {href}")

        return "\n\n".join(formatted)

    except Exception as exc:
        logger.exception("Web search failed: %s", exc)
        return f"Search failed: {exc}"
