"""Date utility commands for the core plugin."""

import typer

app = typer.Typer(no_args_is_help=True)


def _get_dates_module():
    """Lazy import of dates module."""
    from src.core.system.dates import (
        parse_date, get_current_date
    )
    return {
        "parse_date": parse_date,
        "get_current_date": get_current_date,
    }


@app.command("parse")
def parse_cmd(
    reference: str = typer.Argument(..., help="Natural language date (e.g., 'tomorrow', 'next Friday')"),
):
    """Parse a natural language date reference to YYYY-MM-DD format."""
    m = _get_dates_module()
    result = m["parse_date"](reference)

    if "error" in result:
        print(f"Error: {result['error']}")
        if result.get("hint"):
            print(f"Hint: {result['hint']}")
        raise typer.Exit(1)

    print(result.get("date"))


@app.command("current")
def current_cmd():
    """Get the current date."""
    m = _get_dates_module()
    result = m["get_current_date"]()

    print(f"Date: {result.get('date')}")
    print(f"Weekday: {result.get('weekday')}")
    print(f"Formatted: {result.get('formatted')}")
