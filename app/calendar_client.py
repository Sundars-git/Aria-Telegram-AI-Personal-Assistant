"""
calendar_client.py — Google Calendar API integration.

Provides functions to check availability, list upcoming events,
and create new calendar events. Used by the tool dispatcher in tools.py.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from googleapiclient.discovery import build

from app.google_auth import get_credentials

logger = logging.getLogger(__name__)


def _get_service():
    """Build and return a Google Calendar API service object."""
    creds = get_credentials()
    if not creds:
        return None
    return build("calendar", "v3", credentials=creds)


async def check_availability(
    date: str,
    time_start: Optional[str] = None,
    time_end: Optional[str] = None,
) -> str:
    """
    Check calendar availability for a given date and optional time range.

    Args:
        date:       Date string in YYYY-MM-DD format.
        time_start: Optional start time in HH:MM format (24h).
        time_end:   Optional end time in HH:MM format (24h).

    Returns:
        A formatted string describing availability and any conflicts.
    """
    service = _get_service()
    if not service:
        return "Google Calendar is not configured. Please set up OAuth2 credentials."

    try:
        # Parse the date
        target_date = datetime.strptime(date, "%Y-%m-%d").date()

        # Build time range
        if time_start:
            start_dt = datetime.combine(
                target_date,
                datetime.strptime(time_start, "%H:%M").time(),
                tzinfo=timezone.utc,
            )
        else:
            start_dt = datetime.combine(
                target_date,
                datetime.min.time(),
                tzinfo=timezone.utc,
            )

        if time_end:
            end_dt = datetime.combine(
                target_date,
                datetime.strptime(time_end, "%H:%M").time(),
                tzinfo=timezone.utc,
            )
        else:
            end_dt = datetime.combine(
                target_date,
                datetime.max.time(),
                tzinfo=timezone.utc,
            )

        # Query events in the range
        events_result = service.events().list(
            calendarId="primary",
            timeMin=start_dt.isoformat(),
            timeMax=end_dt.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=10,
        ).execute()

        events = events_result.get("items", [])

        if not events:
            time_desc = f" between {time_start} and {time_end}" if time_start else ""
            return f"✅ You're free on {date}{time_desc}. No events scheduled."

        # Format conflicts
        lines = [f"📅 Events on {date}:"]
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date", ""))
            end = event["end"].get("dateTime", event["end"].get("date", ""))
            summary = event.get("summary", "(No title)")

            # Extract just the time portion for display
            if "T" in start:
                start_time = start.split("T")[1][:5]
                end_time = end.split("T")[1][:5]
                lines.append(f"  • {start_time}–{end_time}: {summary}")
            else:
                lines.append(f"  • All day: {summary}")

        return "\n".join(lines)

    except Exception as exc:
        logger.exception("Calendar check failed: %s", exc)
        return f"Failed to check calendar: {exc}"


async def list_upcoming(count: int = 5) -> str:
    """
    List the next N upcoming calendar events.

    Args:
        count: Number of events to return (default 5, max 20).

    Returns:
        Formatted string with upcoming events.
    """
    service = _get_service()
    if not service:
        return "Google Calendar is not configured. Please set up OAuth2 credentials."

    try:
        now = datetime.now(timezone.utc).isoformat()
        count = min(count, 20)

        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=count,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = events_result.get("items", [])

        if not events:
            return "📅 No upcoming events found."

        lines = [f"📅 Next {len(events)} event(s):"]
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date", ""))
            summary = event.get("summary", "(No title)")

            if "T" in start:
                # Parse and format nicely
                dt = datetime.fromisoformat(start)
                formatted = dt.strftime("%a %b %d, %H:%M")
            else:
                formatted = start

            lines.append(f"  • {formatted}: {summary}")

        return "\n".join(lines)

    except Exception as exc:
        logger.exception("Failed to list events: %s", exc)
        return f"Failed to list calendar events: {exc}"


async def create_event(
    title: str,
    start_time: str,
    end_time: str,
    description: Optional[str] = None,
) -> str:
    """
    Create a new Google Calendar event.

    Args:
        title:       Event title/summary.
        start_time:  ISO 8601 datetime string (e.g. 2026-03-05T14:00:00).
        end_time:    ISO 8601 datetime string (e.g. 2026-03-05T15:00:00).
        description: Optional event description.

    Returns:
        Confirmation string with the event link.
    """
    service = _get_service()
    if not service:
        return "Google Calendar is not configured. Please set up OAuth2 credentials."

    try:
        event_body = {
            "summary": title,
            "start": {
                "dateTime": start_time,
                "timeZone": "Asia/Kolkata",
            },
            "end": {
                "dateTime": end_time,
                "timeZone": "Asia/Kolkata",
            },
        }

        if description:
            event_body["description"] = description

        event = service.events().insert(
            calendarId="primary",
            body=event_body,
        ).execute()

        link = event.get("htmlLink", "")
        return (
            f"✅ Event created: **{title}**\n"
            f"   📅 {start_time} → {end_time}\n"
            f"   🔗 {link}"
        )

    except Exception as exc:
        logger.exception("Failed to create event: %s", exc)
        return f"Failed to create calendar event: {exc}"
