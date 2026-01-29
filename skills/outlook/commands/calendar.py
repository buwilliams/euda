"""Outlook calendar commands."""

from typing import Optional

import typer

app = typer.Typer(no_args_is_help=True)


def _get_client():
    """Lazy import of client module."""
    from skills.outlook import client
    return client


@app.command("events")
def events_cmd(
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Account to use"),
    days: int = typer.Option(7, "--days", "-d", help="Number of days to look ahead"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum events to return"),
):
    """List upcoming calendar events."""
    client = _get_client()

    result = client.list_events(
        account_name=account,
        days=days,
        limit=limit,
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Account: {result.get('account')}")
    print(f"Period: {result.get('time_min', '')[:10]} to {result.get('time_max', '')[:10]}")
    print(f"Events ({result.get('count', 0)}):")
    print()

    if not result.get("events"):
        print("  No upcoming events")
        return

    for event in result.get("events", []):
        start = event.get("start", "")
        end = event.get("end", "")
        subject = event.get("subject", "(No title)")
        location = event.get("location", "")
        all_day = event.get("is_all_day", False)

        if all_day:
            print(f"  {start[:10]} (All day)")
        else:
            print(f"  {start[:16]} - {end[11:16]}")

        print(f"    {subject}")
        if location:
            print(f"    Location: {location}")
        print()


@app.command("today")
def today_cmd(
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Account to use"),
):
    """List today's calendar events."""
    client = _get_client()

    result = client.list_events_today(account_name=account)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Account: {result.get('account')}")
    print(f"Date: {result.get('date')}")
    print(f"Events ({result.get('count', 0)}):")
    print()

    if not result.get("events"):
        print("  No events today")
        return

    for event in result.get("events", []):
        start = event.get("start", "")
        end = event.get("end", "")
        subject = event.get("subject", "(No title)")
        location = event.get("location", "")
        all_day = event.get("is_all_day", False)

        if all_day:
            print(f"  All day")
        else:
            print(f"  {start[11:16]} - {end[11:16]}")

        print(f"    {subject}")
        if location:
            print(f"    Location: {location}")
        print()


@app.command("create")
def create_cmd(
    title: str = typer.Argument(..., help="Event title"),
    start: str = typer.Option(..., "--start", "-s", help="Start datetime (e.g., '2026-01-29 10:00' or '2026-01-29T10:00')"),
    end: Optional[str] = typer.Option(None, "--end", "-e", help="End datetime (optional)"),
    duration: int = typer.Option(60, "--duration", "-d", help="Duration in minutes (if end not specified)"),
    location: Optional[str] = typer.Option(None, "--location", "-l", help="Event location"),
    body: Optional[str] = typer.Option(None, "--body", "-b", help="Event description"),
    attendees: Optional[str] = typer.Option(None, "--attendees", "-i", help="Comma-separated attendee emails"),
    all_day: bool = typer.Option(False, "--all-day", help="Create an all-day event"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Account to use"),
):
    """Create a calendar event.

    Attendees will receive email invitations.
    """
    client = _get_client()

    # Parse attendees
    attendee_list = None
    if attendees:
        attendee_list = [addr.strip() for addr in attendees.split(",") if addr.strip()]

    result = client.create_event(
        subject=title,
        start=start,
        end=end,
        duration_minutes=duration,
        location=location,
        body=body,
        attendees=attendee_list,
        is_all_day=all_day,
        account_name=account,
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Created event: {result.get('subject')}")
    print(f"ID: {result.get('id')}")
    print(f"Start: {result.get('start')}")
    print(f"End: {result.get('end')}")
    if result.get("web_link"):
        print(f"Link: {result.get('web_link')}")
