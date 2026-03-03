"""
gmail_client.py — Google Gmail API integration.

Provides functions to read emails, summarize them, and create draft replies.
SAFETY: This module NEVER sends emails — it only creates drafts.
"""

import base64
import logging
from email.mime.text import MIMEText
from typing import Optional

from googleapiclient.discovery import build

from app.google_auth import get_credentials

logger = logging.getLogger(__name__)


def _get_service():
    """Build and return a Gmail API service object."""
    creds = get_credentials()
    if not creds:
        return None
    return build("gmail", "v1", credentials=creds)


async def read_emails(
    query: Optional[str] = None,
    max_results: int = 5,
) -> str:
    """
    Read recent or filtered emails.

    Args:
        query:       Optional Gmail search query (e.g. 'is:unread', 'from:boss@company.com').
                     Defaults to showing recent emails.
        max_results: Number of emails to return (default 5, max 10).

    Returns:
        Formatted string with email summaries.
    """
    service = _get_service()
    if not service:
        return "Gmail is not configured. Please set up OAuth2 credentials."

    try:
        max_results = min(max_results, 10)
        search_query = query or "in:inbox"

        results = service.users().messages().list(
            userId="me",
            q=search_query,
            maxResults=max_results,
        ).execute()

        messages = results.get("messages", [])

        if not messages:
            return f"📭 No emails found for query: '{search_query}'"

        email_summaries = []

        for msg_meta in messages:
            msg = service.users().messages().get(
                userId="me",
                id=msg_meta["id"],
                format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"],
            ).execute()

            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            snippet = msg.get("snippet", "")
            labels = msg.get("labelIds", [])

            # Determine status indicators
            is_unread = "UNREAD" in labels
            is_important = "IMPORTANT" in labels
            status = ""
            if is_unread:
                status += "🔵 "
            if is_important:
                status += "⭐ "

            email_summaries.append(
                f"{status}**{headers.get('Subject', '(No subject)')}**\n"
                f"   From: {headers.get('From', 'Unknown')}\n"
                f"   Date: {headers.get('Date', 'Unknown')}\n"
                f"   Preview: {snippet[:150]}...\n"
                f"   ID: {msg_meta['id']}"
            )

        header = f"📧 {len(email_summaries)} email(s)"
        if query:
            header += f" matching '{query}'"

        return header + "\n\n" + "\n\n".join(email_summaries)

    except Exception as exc:
        logger.exception("Failed to read emails: %s", exc)
        return f"Failed to read emails: {exc}"


async def get_email_body(message_id: str) -> str:
    """
    Get the full text body of an email by its message ID.

    Args:
        message_id: The Gmail message ID.

    Returns:
        The email body text, or an error message.
    """
    service = _get_service()
    if not service:
        return "Gmail is not configured. Please set up OAuth2 credentials."

    try:
        msg = service.users().messages().get(
            userId="me",
            id=message_id,
            format="full",
        ).execute()

        payload = msg.get("payload", {})
        body_text = _extract_body(payload)

        if not body_text:
            return "Could not extract body text from this email."

        # Truncate very long emails
        if len(body_text) > 4000:
            body_text = body_text[:4000] + "\n\n[... truncated ...]"

        return body_text

    except Exception as exc:
        logger.exception("Failed to get email body: %s", exc)
        return f"Failed to get email body: {exc}"


def _extract_body(payload: dict) -> str:
    """Recursively extract plain text body from a Gmail message payload."""
    parts = payload.get("parts", [])

    # Direct body (no parts)
    if not parts:
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
        return ""

    # Multi-part: prefer text/plain, fall back to text/html
    for part in parts:
        mime_type = part.get("mimeType", "")
        if mime_type == "text/plain":
            body_data = part.get("body", {}).get("data", "")
            if body_data:
                return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")

    # Fall back to first text/html part
    for part in parts:
        mime_type = part.get("mimeType", "")
        if mime_type == "text/html":
            body_data = part.get("body", {}).get("data", "")
            if body_data:
                from bs4 import BeautifulSoup
                html = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
                return BeautifulSoup(html, "html.parser").get_text(separator="\n", strip=True)

    # Recurse into nested parts
    for part in parts:
        result = _extract_body(part)
        if result:
            return result

    return ""


async def draft_reply(
    message_id: str,
    reply_body: str,
) -> str:
    """
    Create a draft reply to an email. NEVER sends — only saves as draft.

    Args:
        message_id: The Gmail message ID to reply to.
        reply_body: The text content of the reply.

    Returns:
        Confirmation string.
    """
    service = _get_service()
    if not service:
        return "Gmail is not configured. Please set up OAuth2 credentials."

    try:
        # Get the original message to extract headers
        original = service.users().messages().get(
            userId="me",
            id=message_id,
            format="metadata",
            metadataHeaders=["From", "Subject", "Message-ID"],
        ).execute()

        headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}
        thread_id = original.get("threadId", "")

        # Build reply
        to = headers.get("From", "")
        subject = headers.get("Subject", "")
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        message = MIMEText(reply_body)
        message["to"] = to
        message["subject"] = subject

        # Set In-Reply-To header for threading
        original_msg_id = headers.get("Message-ID", "")
        if original_msg_id:
            message["In-Reply-To"] = original_msg_id
            message["References"] = original_msg_id

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        draft_body = {
            "message": {
                "raw": raw,
                "threadId": thread_id,
            }
        }

        draft = service.users().drafts().create(
            userId="me",
            body=draft_body,
        ).execute()

        draft_id = draft.get("id", "unknown")
        return (
            f"✅ Draft reply created (draft ID: {draft_id})\n"
            f"   To: {to}\n"
            f"   Subject: {subject}\n\n"
            f"⚠️ This is saved as a DRAFT. Open Gmail to review and send."
        )

    except Exception as exc:
        logger.exception("Failed to create draft reply: %s", exc)
        return f"Failed to create draft reply: {exc}"
