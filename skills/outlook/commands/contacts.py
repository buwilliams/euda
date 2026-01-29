"""Outlook contacts commands."""

from typing import Optional

import typer

app = typer.Typer(no_args_is_help=True)


def _get_client():
    """Lazy import of client module."""
    from skills.outlook import client
    return client


@app.command("list")
def list_cmd(
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Account to use"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum contacts to return"),
):
    """List contacts."""
    client = _get_client()

    result = client.list_contacts(
        account_name=account,
        limit=limit,
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Account: {result.get('account')}")
    print(f"Contacts ({result.get('count', 0)}):")
    print()

    if not result.get("contacts"):
        print("  No contacts found")
        return

    for contact in result.get("contacts", []):
        name = contact.get("display_name", "(No name)")
        email = contact.get("email", "")
        phone = contact.get("mobile_phone") or contact.get("business_phone", "")
        company = contact.get("company", "")
        title = contact.get("job_title", "")

        print(f"  {name}")
        if email:
            print(f"    Email: {email}")
        if phone:
            print(f"    Phone: {phone}")
        if company or title:
            info_parts = [p for p in [title, company] if p]
            print(f"    {', '.join(info_parts)}")
        print()


@app.command("search")
def search_cmd(
    query: str = typer.Argument(..., help="Search query (searches display name)"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Account to use"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum results"),
):
    """Search contacts by name."""
    client = _get_client()

    result = client.search_contacts(
        query=query,
        account_name=account,
        limit=limit,
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Account: {result.get('account')}")
    print(f"Search: {result.get('query')}")
    print(f"Results ({result.get('count', 0)}):")
    print()

    if not result.get("contacts"):
        print("  No contacts found")
        return

    for contact in result.get("contacts", []):
        name = contact.get("display_name", "(No name)")
        email = contact.get("email", "")
        phone = contact.get("mobile_phone", "")
        company = contact.get("company", "")

        print(f"  {name}")
        if email:
            print(f"    Email: {email}")
        if phone:
            print(f"    Phone: {phone}")
        if company:
            print(f"    Company: {company}")
        print()
