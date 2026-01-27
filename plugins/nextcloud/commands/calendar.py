"""Nextcloud calendar operations for the nextcloud plugin."""

from typing import Optional
import typer

app = typer.Typer(no_args_is_help=True)


def _get_calendar_module():
    """Lazy import of nextcloud calendar module."""
    from plugins.nextcloud.lib.calendar import (
        nc_list_calendars, nc_list_events, nc_create_event, nc_delete_event
    )
    return {
        "nc_list_calendars": nc_list_calendars,
        "nc_list_events": nc_list_events,
        "nc_create_event": nc_create_event,
        "nc_delete_event": nc_delete_event,
    }


@app.command("list")
def list_cmd(
    instance: Optional[str] = typer.Option(None, "--instance", "-i", help="Nextcloud instance ID"),
):
    """List available calendars."""
    m = _get_calendar_module()
    result = m["nc_list_calendars"](instance=instance)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Instance: {result.get('instance')}")
    print(f"Calendars ({result.get('count', 0)}):")

    for cal in result.get("calendars", []):
        color = cal.get("color") or ""
        print(f"  {cal.get('id')}: {cal.get('name')} {color}")


@app.command("events")
def events_cmd(
    calendar: Optional[str] = typer.Option("personal", "--calendar", "-c", help="Calendar ID"),
    start: Optional[str] = typer.Option(None, "--start", "-s", help="Start date (YYYY-MM-DD)"),
    end: Optional[str] = typer.Option(None, "--end", "-e", help="End date (YYYY-MM-DD)"),
    instance: Optional[str] = typer.Option(None, "--instance", "-i", help="Nextcloud instance ID"),
):
    """List events in a date range."""
    m = _get_calendar_module()
    result = m["nc_list_events"](
        calendar=calendar,
        start_date=start,
        end_date=end,
        instance=instance
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Calendar: {result.get('calendar')}")
    print(f"Range: {result.get('start_date')} to {result.get('end_date')}")
    print(f"Events ({result.get('count', 0)}):")

    for event in result.get("events", []):
        title = event.get("title", "Untitled")
        start_time = event.get("start", "?")
        end_time = event.get("end", "?")
        print(f"  {start_time} - {end_time}: {title}")
        if event.get("location"):
            print(f"    Location: {event['location']}")


@app.command("create-event")
def create_event_cmd(
    title: str = typer.Argument(..., help="Event title"),
    start: str = typer.Argument(..., help="Start datetime (ISO format, e.g., 2024-01-15T10:00:00)"),
    end: Optional[str] = typer.Option(None, "--end", "-e", help="End datetime (default: 1 hour after start)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Event description"),
    location: Optional[str] = typer.Option(None, "--location", "-l", help="Event location"),
    calendar: Optional[str] = typer.Option("personal", "--calendar", "-c", help="Calendar ID"),
    instance: Optional[str] = typer.Option(None, "--instance", "-i", help="Nextcloud instance ID"),
):
    """Create a calendar event."""
    m = _get_calendar_module()
    result = m["nc_create_event"](
        title=title,
        start=start,
        end=end,
        description=description,
        location=location,
        calendar=calendar,
        instance=instance
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Created event: {result.get('title')}")
    print(f"UID: {result.get('uid')}")
    print(f"Start: {result.get('start')}")
    print(f"End: {result.get('end')}")
    print(f"Calendar: {result.get('calendar')}")


@app.command("delete-event")
def delete_event_cmd(
    event_id: str = typer.Argument(..., help="Event UID to delete"),
    calendar: Optional[str] = typer.Option("personal", "--calendar", "-c", help="Calendar ID"),
    instance: Optional[str] = typer.Option(None, "--instance", "-i", help="Nextcloud instance ID"),
):
    """Delete a calendar event."""
    m = _get_calendar_module()
    result = m["nc_delete_event"](
        event_id=event_id,
        calendar=calendar,
        instance=instance
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Deleted event: {result.get('event_id')}")
