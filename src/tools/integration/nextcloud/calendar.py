"""
Nextcloud Calendar Tools - CalDAV calendar operations.
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Optional
import uuid
import requests

from ... import tool
from .client import get_client, NextcloudConfigError


# CalDAV XML namespaces
DAV_NS = "{DAV:}"
CALDAV_NS = "{urn:ietf:params:xml:ns:caldav}"
CS_NS = "{http://calendarserver.org/ns/}"
ICAL_NS = "{http://apple.com/ns/ical/}"


def _parse_calendars_response(xml_text: str) -> List[dict]:
    """Parse PROPFIND response for calendars.

    Args:
        xml_text: XML response body

    Returns:
        List of calendar dicts
    """
    root = ET.fromstring(xml_text)
    calendars = []

    for response in root.findall(f"{DAV_NS}response"):
        href_elem = response.find(f"{DAV_NS}href")
        if href_elem is None:
            continue

        href = href_elem.text or ""

        propstat = response.find(f"{DAV_NS}propstat")
        if propstat is None:
            continue

        prop = propstat.find(f"{DAV_NS}prop")
        if prop is None:
            continue

        # Check if this is a calendar
        resourcetype = prop.find(f"{DAV_NS}resourcetype")
        if resourcetype is None:
            continue

        is_calendar = resourcetype.find(f"{CALDAV_NS}calendar") is not None
        if not is_calendar:
            continue

        displayname = prop.find(f"{DAV_NS}displayname")
        color = prop.find(f"{ICAL_NS}calendar-color")

        # Extract calendar ID from href
        cal_id = href.rstrip("/").split("/")[-1]

        calendars.append({
            "id": cal_id,
            "name": displayname.text if displayname is not None else cal_id,
            "href": href,
            "color": color.text if color is not None else None
        })

    return calendars


def _parse_icalendar_event(ical_text: str) -> Optional[dict]:
    """Parse a simple iCalendar VEVENT into a dict.

    This is a simple parser that handles common fields.
    For complex cases, the icalendar library could be used.

    Args:
        ical_text: iCalendar text

    Returns:
        Event dict or None
    """
    event = {}
    in_vevent = False
    current_key = None
    current_value = ""

    for line in ical_text.split("\n"):
        line = line.rstrip("\r")

        # Handle line continuation
        if line.startswith(" ") or line.startswith("\t"):
            current_value += line[1:]
            continue

        # Process previous key-value
        if current_key and in_vevent:
            _set_event_field(event, current_key, current_value)

        if line == "BEGIN:VEVENT":
            in_vevent = True
            event = {}
        elif line == "END:VEVENT":
            in_vevent = False
            if event:
                return event

        # Parse key:value
        if ":" in line:
            key_part, value = line.split(":", 1)
            # Handle parameters like DTSTART;VALUE=DATE:20240101
            current_key = key_part.split(";")[0]
            current_value = value

    return event if event else None


def _set_event_field(event: dict, key: str, value: str):
    """Set an event field from iCalendar key-value."""
    if key == "UID":
        event["uid"] = value
    elif key == "SUMMARY":
        event["title"] = value
    elif key == "DESCRIPTION":
        event["description"] = value
    elif key == "LOCATION":
        event["location"] = value
    elif key == "DTSTART":
        event["start"] = _parse_ical_datetime(value)
    elif key == "DTEND":
        event["end"] = _parse_ical_datetime(value)
    elif key == "STATUS":
        event["status"] = value.lower()


def _parse_ical_datetime(value: str) -> str:
    """Parse iCalendar datetime to ISO format.

    Args:
        value: iCalendar datetime (e.g., 20240115T100000Z or 20240115)

    Returns:
        ISO format datetime string
    """
    # Remove any timezone suffix for parsing
    value = value.rstrip("Z")

    if "T" in value:
        # DateTime format: 20240115T100000
        try:
            dt = datetime.strptime(value, "%Y%m%dT%H%M%S")
            return dt.isoformat()
        except ValueError:
            return value
    else:
        # Date only: 20240115
        try:
            dt = datetime.strptime(value, "%Y%m%d")
            return dt.date().isoformat()
        except ValueError:
            return value


def _format_ical_datetime(dt_str: str) -> str:
    """Convert ISO datetime to iCalendar format.

    Args:
        dt_str: ISO format datetime

    Returns:
        iCalendar format datetime
    """
    try:
        # Try parsing as datetime
        if "T" in dt_str:
            dt = datetime.fromisoformat(dt_str.replace("Z", ""))
            return dt.strftime("%Y%m%dT%H%M%S")
        else:
            # Date only
            dt = datetime.fromisoformat(dt_str)
            return dt.strftime("%Y%m%d")
    except ValueError:
        return dt_str


def _create_vevent(
    uid: str,
    title: str,
    start: str,
    end: str,
    description: str = None,
    location: str = None
) -> str:
    """Create a VCALENDAR with VEVENT.

    Args:
        uid: Unique identifier
        title: Event summary
        start: Start datetime (ISO format)
        end: End datetime (ISO format)
        description: Optional description
        location: Optional location

    Returns:
        iCalendar text
    """
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    start_ical = _format_ical_datetime(start)
    end_ical = _format_ical_datetime(end)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Euno//Nextcloud Tools//EN",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"DTSTART:{start_ical}",
        f"DTEND:{end_ical}",
        f"SUMMARY:{title}",
    ]

    if description:
        # Escape newlines in description
        desc_escaped = description.replace("\n", "\\n")
        lines.append(f"DESCRIPTION:{desc_escaped}")

    if location:
        lines.append(f"LOCATION:{location}")

    lines.extend([
        "END:VEVENT",
        "END:VCALENDAR"
    ])

    return "\r\n".join(lines)


@tool(
    "nc_list_calendars",
    "List available calendars in Nextcloud. Use when: checking which calendars exist.",
    tool_type="integration"
)
def nc_list_calendars(instance: str = None) -> dict:
    """List all calendars.

    Args:
        instance: Nextcloud instance ID

    Returns:
        Dict with calendars list or error
    """
    try:
        client = get_client(instance)
    except NextcloudConfigError as e:
        return {"error": str(e)}

    try:
        # PROPFIND on calendars root
        propfind_body = """<?xml version="1.0" encoding="UTF-8"?>
<d:propfind xmlns:d="DAV:" xmlns:cs="http://calendarserver.org/ns/" xmlns:c="urn:ietf:params:xml:ns:caldav" xmlns:ic="http://apple.com/ns/ical/">
    <d:prop>
        <d:resourcetype />
        <d:displayname />
        <ic:calendar-color />
    </d:prop>
</d:propfind>"""

        resp = client.caldav_request(
            "PROPFIND",
            "/",
            data=propfind_body,
            headers={
                "Depth": "1",
                "Content-Type": "application/xml; charset=utf-8"
            }
        )

        if resp.status_code == 401:
            return {"error": "Authentication failed - check app password"}
        if resp.status_code not in (200, 207):
            return {"error": f"Request failed with status {resp.status_code}"}

        calendars = _parse_calendars_response(resp.text)
        return {
            "calendars": calendars,
            "count": len(calendars),
            "instance": client.instance.display_name
        }

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out connecting to {client.instance.display_name}"}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to {client.instance.url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except ET.ParseError as e:
        return {"error": f"Failed to parse response: {str(e)}"}


@tool(
    "nc_list_events",
    "List calendar events in a date range. Use when: checking schedule, finding appointments.",
    tool_type="integration"
)
def nc_list_events(
    calendar: str = None,
    start_date: str = None,
    end_date: str = None,
    instance: str = None
) -> dict:
    """List events in a date range.

    Args:
        calendar: Calendar ID (default: 'personal')
        start_date: Start date YYYY-MM-DD (default: today)
        end_date: End date YYYY-MM-DD (default: 7 days from start)
        instance: Nextcloud instance ID

    Returns:
        Dict with events list or error
    """
    try:
        client = get_client(instance)
    except NextcloudConfigError as e:
        return {"error": str(e)}

    # Default calendar
    if calendar is None:
        calendar = "personal"

    # Default date range
    if start_date is None:
        start_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        try:
            start_dt = datetime.fromisoformat(start_date)
        except ValueError:
            return {"error": f"Invalid start_date format: {start_date}. Use YYYY-MM-DD."}

    if end_date is None:
        end_dt = start_dt + timedelta(days=7)
    else:
        try:
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            return {"error": f"Invalid end_date format: {end_date}. Use YYYY-MM-DD."}

    try:
        # CalDAV REPORT request for events in range
        start_ical = start_dt.strftime("%Y%m%dT000000Z")
        end_ical = end_dt.strftime("%Y%m%dT235959Z")

        report_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
    <d:prop>
        <d:getetag />
        <c:calendar-data />
    </d:prop>
    <c:filter>
        <c:comp-filter name="VCALENDAR">
            <c:comp-filter name="VEVENT">
                <c:time-range start="{start_ical}" end="{end_ical}" />
            </c:comp-filter>
        </c:comp-filter>
    </c:filter>
</c:calendar-query>"""

        resp = client.caldav_request(
            "REPORT",
            f"/{calendar}/",
            data=report_body,
            headers={
                "Depth": "1",
                "Content-Type": "application/xml; charset=utf-8"
            }
        )

        if resp.status_code == 404:
            return {"error": f"Calendar not found: {calendar}"}
        if resp.status_code == 401:
            return {"error": "Authentication failed - check app password"}
        if resp.status_code not in (200, 207):
            return {"error": f"Request failed with status {resp.status_code}"}

        # Parse response
        events = []
        root = ET.fromstring(resp.text)

        for response in root.findall(f"{DAV_NS}response"):
            propstat = response.find(f"{DAV_NS}propstat")
            if propstat is None:
                continue

            prop = propstat.find(f"{DAV_NS}prop")
            if prop is None:
                continue

            cal_data = prop.find(f"{CALDAV_NS}calendar-data")
            if cal_data is not None and cal_data.text:
                event = _parse_icalendar_event(cal_data.text)
                if event:
                    events.append(event)

        # Sort by start time
        events.sort(key=lambda e: e.get("start", ""))

        return {
            "calendar": calendar,
            "start_date": start_dt.date().isoformat(),
            "end_date": end_dt.date().isoformat(),
            "events": events,
            "count": len(events),
            "instance": client.instance.display_name
        }

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out connecting to {client.instance.display_name}"}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to {client.instance.url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except ET.ParseError as e:
        return {"error": f"Failed to parse response: {str(e)}"}


@tool(
    "nc_create_event",
    "Create a calendar event in Nextcloud. Use when: scheduling meetings, setting reminders.",
    tool_type="integration"
)
def nc_create_event(
    title: str,
    start: str,
    end: str = None,
    description: str = None,
    location: str = None,
    calendar: str = None,
    instance: str = None
) -> dict:
    """Create a calendar event.

    Args:
        title: Event title
        start: Start datetime (ISO format, e.g., 2024-01-15T10:00:00)
        end: End datetime (ISO format, default: 1 hour after start)
        description: Event description
        location: Event location
        calendar: Calendar ID (default: 'personal')
        instance: Nextcloud instance ID

    Returns:
        Dict with event details or error
    """
    try:
        client = get_client(instance)
    except NextcloudConfigError as e:
        return {"error": str(e)}

    if calendar is None:
        calendar = "personal"

    # Parse and validate start time
    try:
        start_dt = datetime.fromisoformat(start.replace("Z", ""))
    except ValueError:
        return {"error": f"Invalid start format: {start}. Use ISO format (e.g., 2024-01-15T10:00:00)."}

    # Default end time: 1 hour after start
    if end is None:
        end_dt = start_dt + timedelta(hours=1)
        end = end_dt.isoformat()
    else:
        try:
            datetime.fromisoformat(end.replace("Z", ""))
        except ValueError:
            return {"error": f"Invalid end format: {end}. Use ISO format."}

    # Generate unique ID
    uid = f"{uuid.uuid4()}@euno"

    # Create iCalendar content
    ical_content = _create_vevent(uid, title, start, end, description, location)

    try:
        # PUT to create event
        event_filename = f"{uid}.ics"
        resp = client.caldav_request(
            "PUT",
            f"/{calendar}/{event_filename}",
            data=ical_content,
            headers={"Content-Type": "text/calendar; charset=utf-8"}
        )

        if resp.status_code == 404:
            return {"error": f"Calendar not found: {calendar}"}
        if resp.status_code == 401:
            return {"error": "Authentication failed - check app password"}
        if resp.status_code not in (200, 201, 204):
            return {"error": f"Request failed with status {resp.status_code}"}

        return {
            "status": "created",
            "uid": uid,
            "title": title,
            "start": start,
            "end": end,
            "calendar": calendar,
            "instance": client.instance.display_name
        }

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out connecting to {client.instance.display_name}"}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to {client.instance.url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}


@tool(
    "nc_delete_event",
    "Delete a calendar event from Nextcloud. Use when: cancelling appointments.",
    tool_type="integration"
)
def nc_delete_event(event_id: str, calendar: str = None, instance: str = None) -> dict:
    """Delete an event.

    Args:
        event_id: Event UID (from nc_list_events)
        calendar: Calendar ID containing the event (default: 'personal')
        instance: Nextcloud instance ID

    Returns:
        Dict with status or error
    """
    try:
        client = get_client(instance)
    except NextcloudConfigError as e:
        return {"error": str(e)}

    if calendar is None:
        calendar = "personal"

    # Event file is usually uid.ics
    event_filename = f"{event_id}.ics"
    if not event_filename.endswith(".ics"):
        event_filename = f"{event_id}.ics"

    try:
        resp = client.caldav_request("DELETE", f"/{calendar}/{event_filename}")

        if resp.status_code == 404:
            return {"error": f"Event not found: {event_id}"}
        if resp.status_code == 401:
            return {"error": "Authentication failed - check app password"}
        if resp.status_code not in (200, 204):
            return {"error": f"Request failed with status {resp.status_code}"}

        return {
            "status": "deleted",
            "event_id": event_id,
            "calendar": calendar,
            "instance": client.instance.display_name
        }

    except requests.exceptions.Timeout:
        return {"error": f"Request timed out connecting to {client.instance.display_name}"}
    except requests.exceptions.ConnectionError:
        return {"error": f"Could not connect to {client.instance.url}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
