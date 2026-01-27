"""Quote generation commands for the core plugin."""

import os
from typing import Optional
import typer

app = typer.Typer(no_args_is_help=True)


def _get_quote_module():
    """Lazy import of quote module."""
    from plugins.core.system.quote import euno_quote
    return {
        "euno_quote": euno_quote,
    }


@app.command("generate")
def generate_cmd(
    topic_id: Optional[str] = typer.Option(None, "--topic", "-t", help="Topic ID to attach quote to"),
):
    """Generate a personalized daily quote.

    If a topic ID is provided, the quote is saved as an asset on that topic.
    Otherwise, the quote is just printed.
    """
    m = _get_quote_module()

    agent_id = os.environ.get("EUNO_AGENT_ID", "user")

    if topic_id:
        result = m["euno_quote"](agent_id=agent_id, topic_id=topic_id)

        if result.get("status") == "completed":
            print(f'"{result.get("quote")}"')
            print(f"  — {result.get('author')}")
            print(f"\nSaved to topic: {result.get('topic_id')}")
        else:
            print("Failed to generate quote.")
            raise typer.Exit(1)
    else:
        # Generate without saving to topic - call internal helpers directly
        from plugins.core.system.quote import _generate_quote, _get_quote_history
        from plugins.core.data.identity import get_identity

        identity = get_identity("user")
        identity_content = identity.get("content", "") if identity.get("exists") else ""
        history = _get_quote_history(limit=50)
        quote_data = _generate_quote(identity_content, history)

        print(f'"{quote_data.get("quote")}"')
        print(f"  — {quote_data.get('author')}")
