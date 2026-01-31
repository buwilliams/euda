"""Nextcloud integration skill - Files, calendar, and deck operations."""

import sys
from pathlib import Path

import typer

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from skills.nextcloud.commands import files, calendar, deck

app = typer.Typer(
    name="nextcloud",
    help="Nextcloud integration: files, calendar, and deck boards.",
    no_args_is_help=True,
)

# Register command groups
app.add_typer(files.app, name="files", help="WebDAV file operations")
app.add_typer(calendar.app, name="calendar", help="CalDAV calendar operations")
app.add_typer(deck.app, name="deck", help="Deck kanban board operations")


# Instances command group
instances_app = typer.Typer(no_args_is_help=True)
app.add_typer(instances_app, name="instances", help="Manage Nextcloud instances")


@instances_app.command("list")
def list_instances_cmd():
    """List configured Nextcloud instances."""
    from skills.nextcloud.lib.client import list_instances

    instances = list_instances()

    if not instances:
        print("No Nextcloud instances configured.")
        print("Add instances in data/system/config.json under nextcloud.instances")
        return

    print("Configured Nextcloud instances:")
    for inst in instances:
        print(f"  {inst['id']}: {inst['name']} ({inst['url']})")


def main():
    """Entry point for the Nextcloud skill CLI."""
    app()


if __name__ == "__main__":
    main()
