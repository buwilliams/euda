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
