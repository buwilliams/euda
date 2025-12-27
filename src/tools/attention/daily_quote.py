"""Daily quote generator that matches user profile."""

import json
import hashlib
from datetime import date
from pathlib import Path

import anthropic

BASE_DIR = Path(__file__).parent.parent.parent.parent
QUOTES_DIR = BASE_DIR / "data" / "attention" / "state" / "quotes"
PROFILE_DIR = BASE_DIR / "data" / "synthesis" / "state" / "profile"


def get_user_context() -> str:
    """Get relevant user context for quote generation."""
    context_parts = []

    # Read values
    values_file = PROFILE_DIR / "values.md"
    if values_file.exists():
        content = values_file.read_text()
        if content.strip():
            context_parts.append(f"User values:\n{content[:1000]}")

    # Read identity constraints
    constraints_file = PROFILE_DIR / "identity_constraints.md"
    if constraints_file.exists():
        content = constraints_file.read_text()
        if content.strip():
            context_parts.append(f"Identity constraints:\n{content[:500]}")

    # Read behavioral attractors
    attractors_file = PROFILE_DIR / "behavioral_attractors.md"
    if attractors_file.exists():
        content = attractors_file.read_text()
        if content.strip():
            context_parts.append(f"Behavioral patterns:\n{content[:500]}")

    return "\n\n".join(context_parts) if context_parts else ""


def generate_quote(user_context: str) -> dict:
    """Generate a quote using Claude that matches the user's profile."""
    client = anthropic.Anthropic()

    system_prompt = """You are a curator of wisdom. Your task is to provide a single compelling quote that will resonate with the user based on their profile.

The quote should:
- Be from a real person (philosopher, writer, scientist, leader, artist, etc.)
- Be thought-provoking and worthy of reflection
- Connect to the user's values, struggles, or aspirations
- Be concise (1-3 sentences max)

Respond with JSON only:
{
    "quote": "The actual quote text",
    "author": "Author Name",
    "context": "One brief sentence on why this quote was chosen for this user"
}"""

    user_prompt = f"""Based on this user's profile, select a meaningful quote for their day:

{user_context if user_context else "No profile available yet - choose a universally inspiring quote about growth, curiosity, or authentic living."}

Provide a quote that will give them something meaningful to reflect on today."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    # Parse response
    text = response.content[0].text.strip()
    # Handle potential markdown code blocks
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    return json.loads(text)


def get_daily_quote() -> dict:
    """Get the quote for today, generating if needed."""
    QUOTES_DIR.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    quote_file = QUOTES_DIR / f"{today}.json"

    # Return cached quote if exists
    if quote_file.exists():
        return json.loads(quote_file.read_text())

    # Generate new quote
    try:
        user_context = get_user_context()
        quote_data = generate_quote(user_context)
        quote_data["date"] = today
        quote_data["generated"] = True

        # Save for the day
        quote_file.write_text(json.dumps(quote_data, indent=2))
        return quote_data

    except Exception as e:
        # Fallback quote if generation fails
        return {
            "quote": "The only way to do great work is to love what you do.",
            "author": "Steve Jobs",
            "context": "A reminder to align work with passion.",
            "date": today,
            "generated": False,
            "error": str(e)
        }


# Tool definitions for agents
DAILY_QUOTE_TOOLS = [
    {
        "name": "get_daily_quote",
        "description": "Get today's reflection quote for the user",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

DAILY_QUOTE_HANDLERS = {
    "get_daily_quote": lambda **kwargs: json.dumps(get_daily_quote())
}
