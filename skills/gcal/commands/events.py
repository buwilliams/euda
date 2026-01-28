"""Google Calendar event commands."""

from typing import Optional

import typer

app = typer.Typer(no_args_is_help=True)


def _get_client():
    """Lazy import of client module."""
    from skills.gcal import client
    return client


def _get_storage():
    """Lazy import of storage module."""
    from skills.gcal import storage
    return storage


@app.command("list")
def list_cmd(
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Account to use"),
    calendar: str = typer.Option("primary", "--calendar", "-c", help="Calendar name or ID"),
    days: int = typer.Option(7, "--days", "-d", help="Number of days to look ahead"),
):
    """List upcoming events from a calendar.

    Calendar can be a configured name (e.g., 'primary') or a raw calendar ID.
    """
    client = _get_client()
    storage = _get_storage()

    # Resolve calendar name to ID
    calendar_id = storage.resolve_calendar(calendar)

    result = client.list_events(
        account_name=account,
        calendar_id=calendar_id,
        days=days,
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Account: {result.get('account')}")
    print(f"Calendar: {calendar} ({calendar_id})" if calendar != calendar_id else f"Calendar: {calendar_id}")
    print(f"Events ({result.get('count', 0)}):")

    for event in result.get("events", []):
        start = event.get("start", "?")
        end = event.get("end", "?")
        summary = event.get("summary", "(No title)")
        print(f"  {start} - {end}")
        print(f"    {summary}")
        if event.get("location"):
            print(f"    Location: {event['location']}")


@app.command("today")
def today_cmd(
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Account to use"),
):
    """List today's events across all configured calendars."""
    client = _get_client()
    storage = _get_storage()

    calendars = storage.list_configured_calendars()

    if not calendars:
        print("No calendars configured.")
        print("Add calendars with: gcal calendars add <name> <calendar-id>")
        raise typer.Exit(1)

    result = client.list_events_today_from_calendars(
        account_name=account,
        calendars=calendars,
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Account: {result.get('account')}")
    print(f"Date: {result.get('date')}")
    print(f"Events ({result.get('count', 0)}):")

    if not result.get("events"):
        print("  No events today")
        return

    for event in result.get("events", []):
        start = event.get("start", "?")
        end = event.get("end", "?")
        summary = event.get("summary", "(No title)")
        calendar = event.get("calendar", "")
        print(f"  {start} - {end}")
        print(f"    {summary}")
        print(f"    Calendar: {calendar}")
        if event.get("location"):
            print(f"    Location: {event['location']}")


@app.command("create")
def create_cmd(
    title: str = typer.Argument(..., help="Event title"),
    start: str = typer.Option(..., "--start", "-s", help="Start datetime (e.g., '2025-01-29 10:00')"),
    end: Optional[str] = typer.Option(None, "--end", "-e", help="End datetime (default: 1 hour after start)"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Event description"),
    location: Optional[str] = typer.Option(None, "--location", "-l", help="Event location"),
    attendees: Optional[str] = typer.Option(None, "--attendees", "-i", help="Comma-separated attendee emails"),
    calendar: str = typer.Option("primary", "--calendar", "-c", help="Calendar name or ID"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Account to use"),
):
    """Create a calendar event.

    Calendar can be a configured name (e.g., 'primary') or a raw calendar ID.
    Attendees will receive email invitations.
    """
    client = _get_client()
    storage = _get_storage()

    # Resolve calendar name to ID
    calendar_id = storage.resolve_calendar(calendar)

    # Parse attendees
    attendee_list = None
    if attendees:
        attendee_list = [email.strip() for email in attendees.split(",") if email.strip()]

    result = client.create_event(
        title=title,
        start=start,
        end=end,
        description=description,
        location=location,
        attendees=attendee_list,
        calendar_id=calendar_id,
        account_name=account,
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Created event: {result.get('summary')}")
    print(f"ID: {result.get('id')}")
    print(f"Start: {result.get('start')}")
    print(f"End: {result.get('end')}")
    print(f"Calendar: {calendar}")
    if result.get("html_link"):
        print(f"Link: {result.get('html_link')}")
