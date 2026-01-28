"""Google Calendar account management commands."""

from typing import Optional

import typer

app = typer.Typer(no_args_is_help=True)


def _get_storage():
    """Lazy import of storage module."""
    from skills.gcal import storage
    return storage


def _get_auth():
    """Lazy import of auth module."""
    from skills.gcal import auth
    return auth


@app.command("list")
def list_cmd():
    """List configured Google accounts."""
    storage = _get_storage()

    accounts = storage.list_accounts()
    default = storage.get_default_account()

    if not accounts:
        print("No Google accounts configured.")
        print("Add an account with: uv run euno skills gcal accounts add <name>")
        print("Or add a service account: uv run euno skills gcal accounts add-service <name> --key-file <path>")
        return

    print("Configured Google accounts:")
    for account in accounts:
        info = storage.get_account_info(account)
        marker = " (default)" if account == default else ""
        account_type = info.get("type", "unknown") if info else "unknown"
        type_label = "service" if account_type == "service_account" else "oauth"

        if account_type == "service_account" and info:
            email = info.get("email", "")
            print(f"  {account} [{type_label}]{marker}")
            print(f"    Email: {email}")
        else:
            print(f"  {account} [{type_label}]{marker}")


@app.command("add")
def add_cmd(
    name: str = typer.Argument(..., help="Name for this account (e.g., personal, work)"),
):
    """Add a new Google account via OAuth.

    Opens a browser for Google authentication consent.
    Requires GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.
    """
    storage = _get_storage()
    auth = _get_auth()

    # Check if account already exists
    if storage.account_exists(name):
        print(f"Account '{name}' already exists.")
        print(f"Use 'accounts remove {name}' to remove it first.")
        raise typer.Exit(1)

    print(f"Adding Google account '{name}'...")
    print("Opening browser for Google authentication...")
    print()

    # Run OAuth flow
    creds = auth.run_oauth_flow(name)

    if creds:
        print()
        print(f"Successfully added account '{name}'")

        # Set as default if it's the only account
        if len(storage.list_accounts()) == 1:
            storage.set_default_account(name)
            print(f"Set '{name}' as default account")
    else:
        print(f"Failed to add account '{name}'")
        raise typer.Exit(1)


@app.command("add-service")
def add_service_cmd(
    name: str = typer.Argument(..., help="Name for this account (e.g., backend, automation)"),
    key_file: str = typer.Option(..., "--key-file", "-k", help="Path to service account JSON key file"),
):
    """Add a service account using a JSON key file.

    Service accounts are for backend-to-backend integration.
    The calendar must be shared with the service account email.
    """
    storage = _get_storage()

    # Check if account already exists
    if storage.account_exists(name):
        print(f"Account '{name}' already exists.")
        print(f"Use 'accounts remove {name}' to remove it first.")
        raise typer.Exit(1)

    print(f"Adding service account '{name}'...")

    # Save the service account key
    if storage.save_service_account(name, key_file):
        print(f"Successfully added service account '{name}'")

        # Show the service account email
        info = storage.get_account_info(name)
        if info:
            print(f"Service account email: {info.get('email', 'N/A')}")
            print()
            print("Important: Share your calendar with this email to grant access.")

        # Set as default if it's the only account
        if len(storage.list_accounts()) == 1:
            storage.set_default_account(name)
            print(f"Set '{name}' as default account")
    else:
        print(f"Failed to add service account '{name}'")
        print("Make sure the key file exists and is a valid service account JSON file.")
        raise typer.Exit(1)


@app.command("remove")
def remove_cmd(
    name: str = typer.Argument(..., help="Name of the account to remove"),
):
    """Remove a Google account."""
    storage = _get_storage()

    if not storage.account_exists(name):
        print(f"Account '{name}' not found.")
        raise typer.Exit(1)

    if storage.delete_account(name):
        print(f"Removed account '{name}'")
    else:
        print(f"Failed to remove account '{name}'")
        raise typer.Exit(1)


@app.command("default")
def default_cmd(
    name: Optional[str] = typer.Argument(None, help="Account name to set as default"),
):
    """Get or set the default account."""
    storage = _get_storage()

    if name is None:
        # Get current default
        default = storage.get_default_account()
        if default:
            print(f"Default account: {default}")
        else:
            print("No default account set")
    else:
        # Set default
        if not storage.account_exists(name):
            print(f"Account '{name}' not found.")
            raise typer.Exit(1)

        storage.set_default_account(name)
        print(f"Set default account to '{name}'")
