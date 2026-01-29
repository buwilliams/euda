"""Outlook account management commands."""

from typing import Optional

import typer

app = typer.Typer(no_args_is_help=True)


def _get_storage():
    """Lazy import of storage module."""
    from skills.outlook import storage
    return storage


def _get_auth():
    """Lazy import of auth module."""
    from skills.outlook import auth
    return auth


def _get_client():
    """Lazy import of client module."""
    from skills.outlook import client
    return client


@app.command("list")
def list_cmd():
    """List configured Microsoft accounts."""
    storage = _get_storage()

    accounts = storage.list_accounts()
    default = storage.get_default_account()

    if not accounts:
        print("No Microsoft accounts configured.")
        print()
        print("Add an account with:")
        print("  euno skills outlook accounts add <name>")
        print()
        print("Prerequisites:")
        print("  1. Set MICROSOFT_CLIENT_ID environment variable")
        print("  2. Create an app at https://portal.azure.com")
        return

    print("Configured Microsoft accounts:")
    for account in accounts:
        info = storage.get_account_info(account)
        marker = " (default)" if account == default else ""
        email = info.get("email", "") if info else ""

        if email:
            print(f"  {account}{marker}")
            print(f"    Email: {email}")
        else:
            print(f"  {account}{marker}")


@app.command("add")
def add_cmd(
    name: str = typer.Argument(..., help="Name for this account (e.g., personal, work)"),
):
    """Add a new Microsoft account via OAuth.

    Opens a browser authentication flow using device code.
    Requires MICROSOFT_CLIENT_ID environment variable.
    """
    storage = _get_storage()
    auth = _get_auth()

    # Check if account already exists
    if storage.account_exists(name):
        print(f"Account '{name}' already exists.")
        print(f"Use 'accounts remove {name}' to remove it first.")
        raise typer.Exit(1)

    print(f"Adding Microsoft account '{name}'...")

    # Run OAuth flow
    result = auth.run_oauth_flow(name)

    if "access_token" in result:
        print()
        print(f"Successfully added account '{name}'")

        # Try to get user info
        client = _get_client()
        profile = client.get_user_profile(name)
        if "email" in profile:
            print(f"Signed in as: {profile.get('display_name', '')} ({profile.get('email', '')})")

        # Set as default if it's the only account
        if len(storage.list_accounts()) == 1:
            storage.set_default_account(name)
            print(f"Set '{name}' as default account")
    else:
        print()
        print(f"Failed to add account '{name}'")
        print(f"Error: {result.get('error', 'Unknown error')}")
        raise typer.Exit(1)


@app.command("remove")
def remove_cmd(
    name: str = typer.Argument(..., help="Name of the account to remove"),
):
    """Remove a Microsoft account."""
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


@app.command("info")
def info_cmd(
    name: Optional[str] = typer.Argument(None, help="Account name (uses default if not specified)"),
):
    """Show detailed account information."""
    storage = _get_storage()
    client = _get_client()

    account = storage.resolve_account(name)
    if not account:
        print("No account specified and no default account configured.")
        raise typer.Exit(1)

    if not storage.account_exists(account):
        print(f"Account '{account}' not found.")
        raise typer.Exit(1)

    print(f"Account: {account}")

    # Get user profile from API
    profile = client.get_user_profile(account)

    if "error" in profile:
        print(f"  Status: Not authenticated")
        print(f"  Error: {profile['error']}")
    else:
        print(f"  Status: Authenticated")
        print(f"  Name: {profile.get('display_name', 'N/A')}")
        print(f"  Email: {profile.get('email', 'N/A')}")
        if profile.get("job_title"):
            print(f"  Title: {profile.get('job_title')}")
        if profile.get("office_location"):
            print(f"  Office: {profile.get('office_location')}")
