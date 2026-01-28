"""Google Calendar API wrapper."""

from datetime import datetime, timedelta
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from skills.gcal.auth import get_credentials
from skills.gcal.storage import resolve_account


def get_calendar_service(account_name: Optional[str] = None):
    """Get a Google Calendar API service instance.

    Args:
        account_name: Account to use (uses default/only account if not specified)

    Returns:
        Calendar service instance or None if authentication failed
    """
    resolved_account = resolve_account(account_name)
    if not resolved_account:
        return None

    creds = get_credentials(resolved_account)
    if not creds:
        return None

    return build("calendar", "v3", credentials=creds)


def list_calendars(account_name: Optional[str] = None) -> dict:
    """List all calendars for an account.

    Args:
        account_name: Account to use

    Returns:
        Dict with calendars list or error
    """
    resolved_account = resolve_account(account_name)
    if not resolved_account:
        return {"error": "No account specified and no default account configured"}

    service = get_calendar_service(resolved_account)
    if not service:
        return {"error": f"Failed to authenticate account '{resolved_account}'"}

    try:
        calendar_list = service.calendarList().list().execute()
        calendars = []

        for cal in calendar_list.get("items", []):
            calendars.append({
                "id": cal.get("id"),
                "summary": cal.get("summary"),
                "primary": cal.get("primary", False),
                "access_role": cal.get("accessRole"),
                "background_color": cal.get("backgroundColor"),
            })

        return {
            "account": resolved_account,
            "count": len(calendars),
            "calendars": calendars,
        }
    except HttpError as e:
        return {"error": f"API error: {e}"}


def list_events(
    account_name: Optional[str] = None,
    calendar_id: str = "primary",
    days: int = 7,
    max_results: int = 50,
) -> dict:
    """List upcoming events.

    Args:
        account_name: Account to use
        calendar_id: Calendar ID (default: primary)
        days: Number of days to look ahead
        max_results: Maximum events to return

    Returns:
        Dict with events list or error
    """
    resolved_account = resolve_account(account_name)
    if not resolved_account:
        return {"error": "No account specified and no default account configured"}

    service = get_calendar_service(resolved_account)
    if not service:
        return {"error": f"Failed to authenticate account '{resolved_account}'"}

    try:
        now = datetime.utcnow()
        time_min = now.isoformat() + "Z"
        time_max = (now + timedelta(days=days)).isoformat() + "Z"

        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = []
        for event in events_result.get("items", []):
            start = event.get("start", {})
            end = event.get("end", {})

            events.append({
                "id": event.get("id"),
                "summary": event.get("summary", "(No title)"),
                "start": start.get("dateTime", start.get("date")),
                "end": end.get("dateTime", end.get("date")),
                "location": event.get("location"),
                "description": event.get("description"),
                "html_link": event.get("htmlLink"),
            })

        return {
            "account": resolved_account,
            "calendar": calendar_id,
            "time_min": time_min,
            "time_max": time_max,
            "count": len(events),
            "events": events,
        }
    except HttpError as e:
        return {"error": f"API error: {e}"}


def list_events_today(account_name: Optional[str] = None) -> dict:
    """List today's events across all calendars.

    Args:
        account_name: Account to use

    Returns:
        Dict with events list or error
    """
    resolved_account = resolve_account(account_name)
    if not resolved_account:
        return {"error": "No account specified and no default account configured"}

    service = get_calendar_service(resolved_account)
    if not service:
        return {"error": f"Failed to authenticate account '{resolved_account}'"}

    try:
        # Get calendar list
        calendar_list = service.calendarList().list().execute()
        all_calendars = calendar_list.get("items", [])

        # Today's time range
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        time_min = today_start.isoformat() + "Z"
        time_max = today_end.isoformat() + "Z"

        all_events = []

        for cal in all_calendars:
            cal_id = cal.get("id")
            cal_summary = cal.get("summary")

            try:
                events_result = service.events().list(
                    calendarId=cal_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                ).execute()

                for event in events_result.get("items", []):
                    start = event.get("start", {})
                    end = event.get("end", {})

                    all_events.append({
                        "id": event.get("id"),
                        "summary": event.get("summary", "(No title)"),
                        "start": start.get("dateTime", start.get("date")),
                        "end": end.get("dateTime", end.get("date")),
                        "location": event.get("location"),
                        "calendar": cal_summary,
                        "calendar_id": cal_id,
                    })
            except HttpError:
                # Skip calendars we can't access
                continue

        # Sort by start time
        all_events.sort(key=lambda e: e.get("start", ""))

        return {
            "account": resolved_account,
            "date": today_start.strftime("%Y-%m-%d"),
            "count": len(all_events),
            "events": all_events,
        }
    except HttpError as e:
        return {"error": f"API error: {e}"}


def list_events_today_from_calendars(
    account_name: Optional[str] = None,
    calendars: Optional[dict[str, str]] = None,
) -> dict:
    """List today's events from configured calendars.

    Args:
        account_name: Account to use
        calendars: Dict mapping calendar names to calendar IDs

    Returns:
        Dict with events list or error
    """
    if not calendars:
        return {"error": "No calendars configured"}

    resolved_account = resolve_account(account_name)
    if not resolved_account:
        return {"error": "No account specified and no default account configured"}

    service = get_calendar_service(resolved_account)
    if not service:
        return {"error": f"Failed to authenticate account '{resolved_account}'"}

    try:
        # Today's time range
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        time_min = today_start.isoformat() + "Z"
        time_max = today_end.isoformat() + "Z"

        all_events = []

        for cal_name, cal_id in calendars.items():
            try:
                events_result = service.events().list(
                    calendarId=cal_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                ).execute()

                for event in events_result.get("items", []):
                    start = event.get("start", {})
                    end = event.get("end", {})

                    all_events.append({
                        "id": event.get("id"),
                        "summary": event.get("summary", "(No title)"),
                        "start": start.get("dateTime", start.get("date")),
                        "end": end.get("dateTime", end.get("date")),
                        "location": event.get("location"),
                        "calendar": cal_name,
                        "calendar_id": cal_id,
                    })
            except HttpError:
                # Skip calendars we can't access
                continue

        # Sort by start time
        all_events.sort(key=lambda e: e.get("start", ""))

        return {
            "account": resolved_account,
            "date": today_start.strftime("%Y-%m-%d"),
            "count": len(all_events),
            "events": all_events,
        }
    except HttpError as e:
        return {"error": f"API error: {e}"}


def create_event(
    title: str,
    start: str,
    end: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[list[str]] = None,
    calendar_id: str = "primary",
    account_name: Optional[str] = None,
) -> dict:
    """Create a calendar event.

    Args:
        title: Event title
        start: Start datetime (ISO format or YYYY-MM-DD HH:MM)
        end: End datetime (default: 1 hour after start)
        description: Event description
        location: Event location
        attendees: List of attendee email addresses
        calendar_id: Calendar ID
        account_name: Account to use

    Returns:
        Dict with created event or error
    """
    resolved_account = resolve_account(account_name)
    if not resolved_account:
        return {"error": "No account specified and no default account configured"}

    service = get_calendar_service(resolved_account)
    if not service:
        return {"error": f"Failed to authenticate account '{resolved_account}'"}

    try:
        # Parse start time
        start_dt = _parse_datetime(start)
        if not start_dt:
            return {"error": f"Invalid start datetime format: {start}"}

        # Parse or calculate end time
        if end:
            end_dt = _parse_datetime(end)
            if not end_dt:
                return {"error": f"Invalid end datetime format: {end}"}
        else:
            end_dt = start_dt + timedelta(hours=1)

        # Build event body
        event_body = {
            "summary": title,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
        }

        if description:
            event_body["description"] = description
        if location:
            event_body["location"] = location
        if attendees:
            event_body["attendees"] = [{"email": email} for email in attendees]

        # Create the event (sendUpdates sends invitation emails to attendees)
        event = service.events().insert(
            calendarId=calendar_id,
            body=event_body,
            sendUpdates="all" if attendees else "none",
        ).execute()

        return {
            "account": resolved_account,
            "id": event.get("id"),
            "summary": event.get("summary"),
            "start": event.get("start", {}).get("dateTime"),
            "end": event.get("end", {}).get("dateTime"),
            "calendar": calendar_id,
            "html_link": event.get("htmlLink"),
        }
    except HttpError as e:
        return {"error": f"API error: {e}"}


def _parse_datetime(dt_str: str) -> Optional[datetime]:
    """Parse datetime string in various formats.

    Supports:
    - ISO format: 2025-01-29T10:00:00
    - Simple format: 2025-01-29 10:00
    """
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue

    return None
