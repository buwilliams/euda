"""Nextcloud CalDAV calendar operations."""

import re
import uuid
from datetime import datetime, timedelta
from typing import Optional
from xml.etree import ElementTree as ET

from .client import NextcloudClient


def _parse_icalendar_event(ical_data: str) -> dict:
    """Parse basic iCalendar event data.

    Args:
        ical_data: iCalendar formatted string

    Returns:
        Dict with event properties
    """
    event = {}

    # Simple regex parsing for common properties
    patterns = {
        "uid": r"UID:(.+)",
        "title": r"SUMMARY:(.+)",
        "description": r"DESCRIPTION:(.+)",
        "location": r"LOCATION:(.+)",
        "dtstart": r"DTSTART[^:]*:(\d{8}T\d{6}Z?|\d{8})",
        "dtend": r"DTEND[^:]*:(\d{8}T\d{6}Z?|\d{8})",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, ical_data, re.MULTILINE)
        if match:
            event[key] = match.group(1).strip()

    # Parse dates
    for date_key in ("dtstart", "dtend"):
        if date_key in event:
            date_str = event[date_key]
            try:
                if len(date_str) == 8:  # All-day event
                    dt = datetime.strptime(date_str, "%Y%m%d")
                elif date_str.endswith("Z"):
                    dt = datetime.strptime(date_str, "%Y%m%dT%H%M%SZ")
                else:
                    dt = datetime.strptime(date_str, "%Y%m%dT%H%M%S")
                event[date_key.replace("dt", "")] = dt.isoformat()
            except ValueError:
                event[date_key.replace("dt", "")] = date_str

    return event


def nc_list_calendars(instance: Optional[str] = None) -> dict:
    """List available calendars.

    Args:
        instance: Nextcloud instance ID

    Returns:
        Dict with calendars list or error
    """
    try:
        client = NextcloudClient(instance)
    except ValueError as e:
        return {"error": str(e)}

    caldav_path = f"/remote.php/dav/calendars/{client.username}/"

    headers = {
        "Depth": "1",
        "Content-Type": "application/xml",
    }

    propfind_body = b'''<?xml version="1.0" encoding="UTF-8"?>
    <d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav" xmlns:cs="http://calendarserver.org/ns/" xmlns:ic="http://apple.com/ns/ical/">
        <d:prop>
            <d:displayname/>
            <cs:getctag/>
            <ic:calendar-color/>
        </d:prop>
    </d:propfind>'''

    try:
        status, body, _ = client.request(
            "PROPFIND", caldav_path, data=propfind_body, headers=headers
        )
    except ConnectionError as e:
        return {"error": str(e)}

    if status == 401:
        return {"error": "Authentication failed"}
    if status not in (200, 207):
        return {"error": f"Server returned status {status}"}

    # Parse response
    DAV_NS = "{DAV:}"
    ICAL_NS = "{http://apple.com/ns/ical/}"

    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return {"error": "Invalid XML response"}

    calendars = []
    for response in root.findall(f".//{DAV_NS}response"):
        href = response.findtext(f"{DAV_NS}href", "")
        propstat = response.find(f"{DAV_NS}propstat")
        if propstat is None:
            continue

        prop = propstat.find(f"{DAV_NS}prop")
        if prop is None:
            continue

        displayname = prop.findtext(f"{DAV_NS}displayname", "")
        color = prop.findtext(f"{ICAL_NS}calendar-color", "")

        # Extract calendar ID from href
        cal_id = href.rstrip("/").split("/")[-1]

        # Skip the parent directory
        if cal_id == client.username or not cal_id:
            continue

        calendars.append({
            "id": cal_id,
            "name": displayname or cal_id,
            "color": color,
        })

    return {
        "instance": client.instance_id,
        "calendars": calendars,
        "count": len(calendars),
    }


def nc_list_events(
    calendar: str = "personal",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    instance: Optional[str] = None
) -> dict:
    """List events in a date range.

    Args:
        calendar: Calendar ID (default: personal)
        start_date: Start date (YYYY-MM-DD). Default: today
        end_date: End date (YYYY-MM-DD). Default: 7 days from start
        instance: Nextcloud instance ID

    Returns:
        Dict with events list or error
    """
    try:
        client = NextcloudClient(instance)
    except ValueError as e:
        return {"error": str(e)}

    # Default date range
    if start_date is None:
        start_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            return {"error": f"Invalid start_date format: {start_date}"}

    if end_date is None:
        end_dt = start_dt + timedelta(days=7)
    else:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return {"error": f"Invalid end_date format: {end_date}"}

    caldav_path = f"/remote.php/dav/calendars/{client.username}/{calendar}/"

    headers = {
        "Depth": "1",
        "Content-Type": "application/xml",
    }

    # CalDAV REPORT request for events in range
    report_body = f'''<?xml version="1.0" encoding="UTF-8"?>
    <c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
        <d:prop>
            <d:getetag/>
            <c:calendar-data/>
        </d:prop>
        <c:filter>
            <c:comp-filter name="VCALENDAR">
                <c:comp-filter name="VEVENT">
                    <c:time-range start="{start_dt.strftime('%Y%m%dT000000Z')}" end="{end_dt.strftime('%Y%m%dT235959Z')}"/>
                </c:comp-filter>
            </c:comp-filter>
        </c:filter>
    </c:calendar-query>'''.encode()

    try:
        status, body, _ = client.request(
            "REPORT", caldav_path, data=report_body, headers=headers
        )
    except ConnectionError as e:
        return {"error": str(e)}

    if status == 404:
        return {"error": f"Calendar not found: {calendar}"}
    if status == 401:
        return {"error": "Authentication failed"}
    if status not in (200, 207):
        return {"error": f"Server returned status {status}"}

    # Parse response
    DAV_NS = "{DAV:}"
    CALDAV_NS = "{urn:ietf:params:xml:ns:caldav}"

    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return {"error": "Invalid XML response"}

    events = []
    for response in root.findall(f".//{DAV_NS}response"):
        propstat = response.find(f"{DAV_NS}propstat")
        if propstat is None:
            continue

        prop = propstat.find(f"{DAV_NS}prop")
        if prop is None:
            continue

        calendar_data = prop.findtext(f"{CALDAV_NS}calendar-data", "")
        if calendar_data:
            event = _parse_icalendar_event(calendar_data)
            if event:
                events.append(event)

    # Sort by start time
    events.sort(key=lambda e: e.get("start", ""))

    return {
        "calendar": calendar,
        "instance": client.instance_id,
        "start_date": start_dt.strftime("%Y-%m-%d"),
        "end_date": end_dt.strftime("%Y-%m-%d"),
        "events": events,
        "count": len(events),
    }


def nc_create_event(
    title: str,
    start: str,
    end: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    calendar: str = "personal",
    instance: Optional[str] = None
) -> dict:
    """Create a calendar event.

    Args:
        title: Event title
        start: Start datetime (ISO format)
        end: End datetime (default: 1 hour after start)
        description: Event description
        location: Event location
        calendar: Calendar ID
        instance: Nextcloud instance ID

    Returns:
        Dict with created event info or error
    """
    try:
        client = NextcloudClient(instance)
    except ValueError as e:
        return {"error": str(e)}

    # Parse start time
    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
    except ValueError:
        return {"error": f"Invalid start datetime: {start}"}

    # Parse or default end time
    if end:
        try:
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        except ValueError:
            return {"error": f"Invalid end datetime: {end}"}
    else:
        end_dt = start_dt + timedelta(hours=1)

    # Generate UID
    event_uid = str(uuid.uuid4())

    # Build iCalendar
    ical_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Euno//Nextcloud Skill//EN",
        "BEGIN:VEVENT",
        f"UID:{event_uid}",
        f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{title}",
    ]

    if description:
        ical_lines.append(f"DESCRIPTION:{description}")
    if location:
        ical_lines.append(f"LOCATION:{location}")

    ical_lines.extend(["END:VEVENT", "END:VCALENDAR"])
    ical_content = "\r\n".join(ical_lines)

    caldav_path = f"/remote.php/dav/calendars/{client.username}/{calendar}/{event_uid}.ics"

    headers = {"Content-Type": "text/calendar; charset=utf-8"}

    try:
        status, _, _ = client.request(
            "PUT", caldav_path, data=ical_content.encode(), headers=headers
        )
    except ConnectionError as e:
        return {"error": str(e)}

    if status == 404:
        return {"error": f"Calendar not found: {calendar}"}
    if status == 401:
        return {"error": "Authentication failed"}
    if status not in (200, 201, 204):
        return {"error": f"Server returned status {status}"}

    return {
        "uid": event_uid,
        "title": title,
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "calendar": calendar,
        "instance": client.instance_id,
    }


def nc_delete_event(
    event_id: str,
    calendar: str = "personal",
    instance: Optional[str] = None
) -> dict:
    """Delete a calendar event.

    Args:
        event_id: Event UID
        calendar: Calendar ID
        instance: Nextcloud instance ID

    Returns:
        Dict with status or error
    """
    try:
        client = NextcloudClient(instance)
    except ValueError as e:
        return {"error": str(e)}

    caldav_path = f"/remote.php/dav/calendars/{client.username}/{calendar}/{event_id}.ics"

    try:
        status, _, _ = client.request("DELETE", caldav_path)
    except ConnectionError as e:
        return {"error": str(e)}

    if status == 404:
        return {"error": f"Event not found: {event_id}"}
    if status == 401:
        return {"error": "Authentication failed"}
    if status not in (200, 204):
        return {"error": f"Server returned status {status}"}

    return {
        "status": "deleted",
        "event_id": event_id,
        "calendar": calendar,
        "instance": client.instance_id,
    }
