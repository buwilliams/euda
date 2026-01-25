"""
Quote Tool - System tool for generating personalized daily quotes.

This tool generates quotes personalized to the user's identity and
saves them as topic assets for later retrieval via the API.
"""

import json
from pathlib import Path

from .. import tool
from ...llms import get_client
from ...tools.data.identity import get_identity
from ...tools.data.topics import list_topics
from ...tools.data.assets import write_asset, read_asset


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"


def _get_quote_history(limit: int = 50) -> list:
    """Get recent quote history from completed euno:quote topics.

    Args:
        limit: Maximum number of quotes to return

    Returns:
        List of quote dicts with 'quote' and 'author' keys
    """
    history = []

    # Get completed topics and filter for quote topics
    all_topics = list_topics(status="done")
    quote_topics = [t for t in all_topics if t.get("name", "").startswith("euno:quote")]

    for topic in quote_topics[:limit]:
        try:
            asset = read_asset(topic["id"], "quote.json")
            if asset and asset.get("content"):
                quote_data = json.loads(asset["content"])
                if quote_data.get("quote") and quote_data.get("author"):
                    history.append({
                        "quote": quote_data["quote"],
                        "author": quote_data["author"]
                    })
        except (json.JSONDecodeError, KeyError):
            continue

    return history


def _generate_quote(identity_content: str, history: list) -> dict:
    """Generate a personalized quote using the configured LLM.

    Args:
        identity_content: User's identity for personalization
        history: Previous quotes to avoid repetition

    Returns:
        Dict with 'quote' and 'author' keys
    """
    client = get_client()

    # Build context about recently used quotes to avoid
    history_context = ""
    if history:
        history_context = "\n\nQuotes to AVOID (recently used):\n"
        for q in history:
            history_context += f"- \"{q['quote']}\" - {q['author']}\n"

    prompt = f"""Based on this user's identity, select or compose an inspiring quote that would resonate with them today.

User Identity:
{identity_content if identity_content else "No identity available - provide a generally inspiring quote."}
{history_context}

Respond with ONLY a JSON object in this exact format (no markdown, no explanation):
{{"quote": "The quote text here", "author": "Author Name"}}

The quote can be from a famous person, philosopher, writer, or you can compose an original one attributed to "Unknown" or "Ancient Wisdom". Make it meaningful and relevant to the user's interests, goals, concerns, or values."""

    response = client.create(
        max_tokens=256,
        system="You are a helpful assistant that provides inspiring quotes.",
        messages=[{"role": "user", "content": prompt}],
        agent_id="user"  # Use user agent for cost tracking
    )

    text = response.content[0].text.strip()

    # Parse JSON response
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback if parsing fails
        return {
            "quote": "The journey of a thousand miles begins with a single step.",
            "author": "Lao Tzu"
        }


@tool(
    "euno_quote",
    "Generate a personalized daily quote. Internal system tool for scheduled quote topics.",
    tool_type="system"
)
def euno_quote(agent_id: str, topic_id: str) -> dict:
    """Generate a personalized quote and save as topic asset.

    This tool is called by the system when processing euno:quote topics.
    It generates a quote personalized to the user's identity and saves
    it as an asset on the triggering topic.

    Args:
        agent_id: The agent generating the quote (for identity context)
        topic_id: The topic to attach the quote asset to

    Returns:
        Dict with the generated quote
    """
    # Get user identity for personalization
    identity = get_identity("user")
    identity_content = identity.get("content", "") if identity.get("exists") else ""

    # Get quote history to avoid repetition
    history = _get_quote_history(limit=50)

    # Generate quote
    quote_data = _generate_quote(identity_content, history)

    # Save as topic asset
    write_asset(topic_id, "quote.json", json.dumps(quote_data, indent=2))

    return {
        "status": "completed",
        "quote": quote_data.get("quote"),
        "author": quote_data.get("author"),
        "topic_id": topic_id
    }
