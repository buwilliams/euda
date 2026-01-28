"""Google Calendar calendar commands."""

from typing import Optional

import typer

app = typer.Typer(no_args_is_help=True)


def _get_client():
    """Lazy import of client module."""
    from plugins.gcal import client
    return client


def _get_storage():
    """Lazy import of storage module."""
    from plugins.gcal import storage
    return storage


@app.command("list")
def list_cmd():
    """List configured calendars."""
    storage = _get_storage()

    calendars = storage.list_configured_calendars()

    if not calendars:
        print("No calendars configured.")
        print("Add a calendar with: gcal calendars add <name> <calendar-id>")
        return

    print("Configured calendars:")
    for name, calendar_id in calendars.items():
        print(f"  {name}: {calendar_id}")


@app.command("add")
def add_cmd(
    name: str = typer.Argument(..., help="Friendly name for the calendar (e.g., primary, work)"),
    calendar_id: str = typer.Argument(..., help="Google Calendar ID (usually an email address)"),
):
    """Add a calendar to the configuration."""
    storage = _get_storage()

    storage.add_calendar(name, calendar_id)
    print(f"Added calendar '{name}': {calendar_id}")


@app.command("remove")
def remove_cmd(
    name: str = typer.Argument(..., help="Name of the calendar to remove"),
):
    """Remove a calendar from the configuration."""
    storage = _get_storage()

    if storage.remove_calendar(name):
        print(f"Removed calendar '{name}'")
    else:
        print(f"Calendar '{name}' not found")
        raise typer.Exit(1)


@app.command("discover")
def discover_cmd(
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Account to use"),
):
    """Discover calendars from Google (API call).

    Lists calendars visible to the account. For service accounts,
    this may be empty - use calendar IDs directly instead.
    """
    client = _get_client()

    result = client.list_calendars(account_name=account)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Account: {result.get('account')}")
    print(f"Discovered calendars ({result.get('count', 0)}):")

    for cal in result.get("calendars", []):
        primary = " (primary)" if cal.get("primary") else ""
        print(f"  {cal.get('summary')}{primary}")
        print(f"    ID: {cal.get('id')}")
        if cal.get("background_color"):
            print(f"    Color: {cal.get('background_color')}")
