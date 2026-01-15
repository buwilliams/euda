"""
Date Tools - Utilities for parsing and working with dates.

Provides tools for agents to convert natural language date references
(like "today", "tomorrow", "next Friday") into proper YYYY-MM-DD format.
"""

import re
from datetime import datetime, timedelta

from .. import tool


WEEKDAYS = {
    'monday': 0, 'mon': 0,
    'tuesday': 1, 'tue': 1, 'tues': 1,
    'wednesday': 2, 'wed': 2,
    'thursday': 3, 'thu': 3, 'thur': 3, 'thurs': 3,
    'friday': 4, 'fri': 4,
    'saturday': 5, 'sat': 5,
    'sunday': 6, 'sun': 6,
}


def _get_next_weekday(from_date: datetime, weekday: int) -> datetime:
    """Get the next occurrence of a weekday (0=Monday, 6=Sunday)."""
    days_ahead = weekday - from_date.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return from_date + timedelta(days=days_ahead)


def _get_end_of_week(from_date: datetime) -> datetime:
    """Get end of current week (Sunday)."""
    days_until_sunday = 6 - from_date.weekday()
    if days_until_sunday < 0:
        days_until_sunday += 7
    return from_date + timedelta(days=days_until_sunday)


def _parse_date_reference(reference: str) -> str:
    """
    Parse a natural language date reference into YYYY-MM-DD format.

    Supports:
    - "today", "now" → current date
    - "tomorrow" → current date + 1
    - "yesterday" → current date - 1
    - "next week" → current date + 7
    - "this week", "end of week" → end of current week (Sunday)
    - "next monday", "next friday", etc. → next occurrence of weekday
    - "in X days" → current date + X days
    - "in X weeks" → current date + X*7 days
    - Already formatted "YYYY-MM-DD" → pass through
    """
    today = datetime.now().date()
    ref = reference.lower().strip()

    # Already in YYYY-MM-DD format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', ref):
        return ref

    # Today/now
    if ref in ('today', 'now', 'tonight'):
        return today.isoformat()

    # Tomorrow
    if ref == 'tomorrow':
        return (today + timedelta(days=1)).isoformat()

    # Yesterday
    if ref == 'yesterday':
        return (today - timedelta(days=1)).isoformat()

    # Next week
    if ref == 'next week':
        return (today + timedelta(days=7)).isoformat()

    # This week / end of week
    if ref in ('this week', 'end of week', 'end of the week'):
        return _get_end_of_week(datetime.now()).date().isoformat()

    # "in X days" pattern
    days_match = re.match(r'in\s+(\d+)\s+days?', ref)
    if days_match:
        days = int(days_match.group(1))
        return (today + timedelta(days=days)).isoformat()

    # "in X weeks" pattern
    weeks_match = re.match(r'in\s+(\d+)\s+weeks?', ref)
    if weeks_match:
        weeks = int(weeks_match.group(1))
        return (today + timedelta(weeks=weeks)).isoformat()

    # "next [weekday]" pattern
    next_weekday_match = re.match(r'next\s+(\w+)', ref)
    if next_weekday_match:
        weekday_name = next_weekday_match.group(1).lower()
        if weekday_name in WEEKDAYS:
            target_date = _get_next_weekday(datetime.now(), WEEKDAYS[weekday_name])
            return target_date.date().isoformat()

    # Just a weekday name (implies next occurrence)
    if ref in WEEKDAYS:
        target_date = _get_next_weekday(datetime.now(), WEEKDAYS[ref])
        return target_date.date().isoformat()

    # "this [weekday]" pattern - same as next weekday
    this_weekday_match = re.match(r'this\s+(\w+)', ref)
    if this_weekday_match:
        weekday_name = this_weekday_match.group(1).lower()
        if weekday_name in WEEKDAYS:
            target_date = _get_next_weekday(datetime.now(), WEEKDAYS[weekday_name])
            return target_date.date().isoformat()

    # Couldn't parse - return None indicator
    return None


@tool("parse_date", "Convert a natural language date reference to YYYY-MM-DD format. Use when: setting due dates from user input like 'tomorrow' or 'next Friday'.", tool_type="system")
def parse_date(reference: str) -> dict:
    """
    Parse a natural language date reference into YYYY-MM-DD format.

    Args:
        reference: Natural language date like "today", "tomorrow", "next Friday",
                   "in 3 days", etc. Or an already formatted YYYY-MM-DD date.

    Returns:
        dict with 'date' (YYYY-MM-DD string) or 'error' if unparseable
    """
    result = _parse_date_reference(reference)

    if result:
        return {
            "date": result,
            "parsed_from": reference
        }
    else:
        return {
            "error": f"Could not parse date reference: '{reference}'",
            "hint": "Supported formats: 'today', 'tomorrow', 'yesterday', 'next week', 'this week', 'next Monday', 'in 3 days', 'in 2 weeks', weekday names, or YYYY-MM-DD"
        }


@tool("get_current_date", "Get the current date in YYYY-MM-DD format with weekday. Use when: need to know today's date for scheduling or relative date calculations.", tool_type="system")
def get_current_date() -> dict:
    """
    Get the current date.

    Returns:
        dict with 'date' (YYYY-MM-DD), 'weekday', and 'formatted' (human readable)
    """
    today = datetime.now()
    return {
        "date": today.date().isoformat(),
        "weekday": today.strftime("%A"),
        "formatted": today.strftime("%B %d, %Y")
    }


# Time constants for named times
NAMED_TIMES = {
    'midnight': (0, 0),
    'morning': (9, 0),
    'noon': (12, 0),
    'midday': (12, 0),
    'afternoon': (14, 0),
    'evening': (18, 0),
    'night': (20, 0),
    'tonight': (20, 0),
}


def _parse_time_reference(reference: str) -> tuple:
    """
    Parse a time reference into (hour, minute) tuple.

    Supports:
    - "3pm", "3:30pm", "3:30 pm" → (15, 0) or (15, 30)
    - "15:30", "15:00" → (15, 30) or (15, 0)
    - "morning", "noon", "evening", etc. → named times
    - "in X hours" → current time + X hours
    - "in X minutes" → current time + X minutes

    Returns:
        (hour, minute) tuple or None if not parseable
    """
    ref = reference.lower().strip()

    # Named times
    if ref in NAMED_TIMES:
        return NAMED_TIMES[ref]

    # 24-hour format: "15:30" or "15:00"
    match_24h = re.match(r'^(\d{1,2}):(\d{2})$', ref)
    if match_24h:
        hour = int(match_24h.group(1))
        minute = int(match_24h.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return (hour, minute)

    # 12-hour format: "3pm", "3:30pm", "3:30 pm", "3 pm"
    match_12h = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$', ref)
    if match_12h:
        hour = int(match_12h.group(1))
        minute = int(match_12h.group(2)) if match_12h.group(2) else 0
        period = match_12h.group(3)

        if hour == 12:
            hour = 0 if period == 'am' else 12
        elif period == 'pm':
            hour += 12

        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return (hour, minute)

    # "in X hours" pattern
    hours_match = re.match(r'^in\s+(\d+)\s+hours?$', ref)
    if hours_match:
        hours = int(hours_match.group(1))
        future = datetime.now() + timedelta(hours=hours)
        return (future.hour, future.minute)

    # "in X minutes" pattern
    minutes_match = re.match(r'^in\s+(\d+)\s+(?:minutes?|mins?)$', ref)
    if minutes_match:
        minutes = int(minutes_match.group(1))
        future = datetime.now() + timedelta(minutes=minutes)
        return (future.hour, future.minute)

    return None


def _parse_datetime_reference(reference: str) -> str:
    """
    Parse a natural language datetime reference into ISO format.

    Supports combinations like:
    - "tomorrow at 3pm"
    - "next friday at 14:30"
    - "in 2 hours"
    - "3pm" (today)
    - "tomorrow morning"

    Returns:
        ISO datetime string (YYYY-MM-DDTHH:MM:SS) or None
    """
    ref = reference.lower().strip()
    now = datetime.now()

    # Already in ISO datetime format
    if re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$', ref):
        return ref if ref.count(':') == 2 else ref + ':00'

    # Check for "in X hours/minutes" - these are relative to now
    if ref.startswith('in '):
        time_result = _parse_time_reference(ref)
        if time_result:
            hour, minute = time_result
            # For "in X hours/minutes", use today's date with calculated time
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()

    # Try to split into date and time parts
    # Patterns: "tomorrow at 3pm", "next friday at noon", "monday 3pm"
    at_match = re.match(r'^(.+?)\s+at\s+(.+)$', ref)
    if at_match:
        date_part = at_match.group(1).strip()
        time_part = at_match.group(2).strip()
    else:
        # Try "tomorrow morning", "next friday 3pm" without "at"
        # Check if last word(s) are a time
        words = ref.split()
        time_result = None
        date_part = ref
        time_part = None

        # Try last word as time
        if len(words) >= 2:
            potential_time = words[-1]
            time_result = _parse_time_reference(potential_time)
            if time_result:
                date_part = ' '.join(words[:-1])
                time_part = potential_time

        # Try last two words as time (e.g., "3 pm")
        if not time_result and len(words) >= 3:
            potential_time = ' '.join(words[-2:])
            time_result = _parse_time_reference(potential_time)
            if time_result:
                date_part = ' '.join(words[:-2])
                time_part = potential_time

    # Parse the date part
    date_str = _parse_date_reference(date_part) if date_part else now.date().isoformat()

    # If no date could be parsed, maybe it's just a time for today
    if not date_str:
        time_result = _parse_time_reference(ref)
        if time_result:
            hour, minute = time_result
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()
        return None

    # Parse the time part
    if time_part:
        time_result = _parse_time_reference(time_part)
        if time_result:
            hour, minute = time_result
        else:
            return None  # Had time part but couldn't parse it
    else:
        # No time specified - default to 9am for dates, or if it's a time-only input
        time_result = _parse_time_reference(ref)
        if time_result:
            hour, minute = time_result
            date_str = now.date().isoformat()
        else:
            hour, minute = 9, 0  # Default time for date-only references

    # Combine date and time
    return f"{date_str}T{hour:02d}:{minute:02d}:00"


@tool("parse_datetime", "Convert a natural language datetime reference to ISO format for scheduling. Use when: scheduling reminders like 'tomorrow at 3pm' or 'in 2 hours'.", tool_type="system")
def parse_datetime(reference: str) -> dict:
    """
    Parse a natural language datetime reference into ISO format.

    Args:
        reference: Natural language datetime like "tomorrow at 3pm", "next Friday at noon",
                   "in 2 hours", "3:30pm", "monday morning", etc.

    Returns:
        dict with 'datetime' (ISO string) and 'formatted' (human readable) or 'error'
    """
    result = _parse_datetime_reference(reference)

    if result:
        # Parse the result to create human-readable format
        dt = datetime.fromisoformat(result)
        formatted = dt.strftime("%A, %B %d at %I:%M %p")

        return {
            "datetime": result,
            "formatted": formatted,
            "parsed_from": reference
        }
    else:
        return {
            "error": f"Could not parse datetime reference: '{reference}'",
            "hint": "Supported formats: 'tomorrow at 3pm', 'next Friday at noon', 'in 2 hours', '3:30pm', 'monday morning', 'in 30 minutes', or ISO format"
        }
