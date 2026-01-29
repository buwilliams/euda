"""Outlook mail commands."""

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
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum messages to return"),
    unread: bool = typer.Option(False, "--unread", "-u", help="Show only unread messages"),
    folder: str = typer.Option("inbox", "--folder", "-f", help="Mail folder (inbox, drafts, sentitems, deleteditems)"),
):
    """List email messages."""
    client = _get_client()

    result = client.list_messages(
        account_name=account,
        limit=limit,
        unread_only=unread,
        folder=folder,
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Account: {result.get('account')}")
    print(f"Folder: {result.get('folder')}")
    print(f"Messages ({result.get('count', 0)}):")
    print()

    if not result.get("messages"):
        print("  No messages found")
        return

    for msg in result.get("messages", []):
        read_marker = " " if msg.get("is_read") else "*"
        attach_marker = " [+]" if msg.get("has_attachments") else ""

        print(f"{read_marker} {msg.get('received', '')[:16]}")
        print(f"  From: {msg.get('from_name', '')} <{msg.get('from_email', '')}>")
        print(f"  Subject: {msg.get('subject', '(No subject)')}{attach_marker}")
        print(f"  ID: {msg.get('id', '')[:20]}...")
        print()


@app.command("read")
def read_cmd(
    message_id: str = typer.Argument(..., help="Message ID to read"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Account to use"),
):
    """Read a specific email message."""
    client = _get_client()

    result = client.get_message(message_id, account_name=account)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"From: {result.get('from_name', '')} <{result.get('from_email', '')}>")
    print(f"To: {', '.join(result.get('to', []))}")
    if result.get("cc"):
        print(f"Cc: {', '.join(result.get('cc', []))}")
    print(f"Date: {result.get('received', '')}")
    print(f"Subject: {result.get('subject', '(No subject)')}")
    print()
    print("-" * 60)
    print()

    body = result.get("body", "")
    body_type = result.get("body_type", "text")

    if body_type.lower() == "html":
        # Strip HTML tags for display (basic)
        import re
        body = re.sub(r'<style[^>]*>.*?</style>', '', body, flags=re.DOTALL)
        body = re.sub(r'<[^>]+>', '', body)
        body = body.strip()

    print(body)


@app.command("send")
def send_cmd(
    to: str = typer.Argument(..., help="Recipient email address(es), comma-separated"),
    subject: str = typer.Option(..., "--subject", "-s", help="Email subject"),
    body: str = typer.Option(..., "--body", "-b", help="Email body"),
    cc: Optional[str] = typer.Option(None, "--cc", help="CC email address(es), comma-separated"),
    html: bool = typer.Option(False, "--html", help="Send as HTML email"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Account to use"),
):
    """Send an email message."""
    client = _get_client()

    # Parse recipients
    to_list = [addr.strip() for addr in to.split(",") if addr.strip()]
    cc_list = [addr.strip() for addr in cc.split(",") if addr.strip()] if cc else None

    result = client.send_message(
        to=to_list,
        subject=subject,
        body=body,
        cc=cc_list,
        body_type="html" if html else "text",
        account_name=account,
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Email sent successfully!")
    print(f"To: {', '.join(result.get('to', []))}")
    print(f"Subject: {result.get('subject', '')}")


@app.command("search")
def search_cmd(
    query: str = typer.Argument(..., help="Search query (e.g., 'from:someone@example.com')"),
    account: Optional[str] = typer.Option(None, "--account", "-a", help="Account to use"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum results"),
):
    """Search email messages.

    Examples:
      - "from:boss@company.com"
      - "subject:meeting"
      - "important project"
    """
    client = _get_client()

    result = client.search_messages(
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

    if not result.get("messages"):
        print("  No messages found")
        return

    for msg in result.get("messages", []):
        read_marker = " " if msg.get("is_read") else "*"

        print(f"{read_marker} {msg.get('received', '')[:16]}")
        print(f"  From: {msg.get('from_name', '')} <{msg.get('from_email', '')}>")
        print(f"  Subject: {msg.get('subject', '(No subject)')}")
        print(f"  ID: {msg.get('id', '')[:20]}...")
        print()
