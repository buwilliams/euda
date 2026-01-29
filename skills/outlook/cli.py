"""Microsoft Outlook integration skill - Mail, Calendar, and Contacts via Microsoft Graph API."""

import sys
from pathlib import Path

import typer

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from skills.outlook.commands import accounts, mail, calendar, contacts

app = typer.Typer(
    name="outlook",
    help="Microsoft Outlook integration - Mail, Calendar, and Contacts via Microsoft Graph API.",
    no_args_is_help=True,
)

# Register command groups
app.add_typer(accounts.app, name="accounts", help="Manage Microsoft accounts")
app.add_typer(mail.app, name="mail", help="Email operations")
app.add_typer(calendar.app, name="calendar", help="Calendar operations")
app.add_typer(contacts.app, name="contacts", help="Contact operations")


def main():
    """Entry point for the Outlook skill CLI."""
    app()


if __name__ == "__main__":
    main()
