"""Daily quote generator that matches user profile."""

import json
import hashlib
from datetime import date, timedelta
from pathlib import Path

import anthropic

BASE_DIR = Path(__file__).parent.parent.parent.parent
QUOTES_DIR = BASE_DIR / "data" / "attention" / "state" / "quotes"
PROFILE_DIR = BASE_DIR / "data" / "synthesis" / "state" / "profile"


def get_user_context() -> str:
    """Get relevant user context for quote generation."""
    context_parts = []

    # Read current profile (contains identity constraints, values, behavioral attractors)
    profile_file = PROFILE_DIR / "profile.current.md"
    if profile_file.exists():
        content = profile_file.read_text()
        if content.strip():
            # Extract key sections (first ~3000 chars covers the important parts)
            context_parts.append(f"User profile:\n{content[:3000]}")

    # Read influences timeline (thinkers, books, ideas they resonate with)
    influences_file = PROFILE_DIR / "influences_timeline.md"
    if influences_file.exists():
        content = influences_file.read_text()
        if content.strip():
            # Include influences to help select relevant authors
            context_parts.append(f"Intellectual influences and interests:\n{content[:2000]}")

    return "\n\n".join(context_parts) if context_parts else ""


def get_recent_quotes(days: int = 7) -> list:
    """Get quotes from the last N days to avoid repetition."""
    recent = []
    today = date.today()
    for i in range(1, days + 1):
        past_date = today - timedelta(days=i)
        quote_file = QUOTES_DIR / f"{past_date.isoformat()}.json"
        if quote_file.exists():
            try:
                data = json.loads(quote_file.read_text())
                recent.append(f"- \"{data.get('quote', '')}\" — {data.get('author', '')}")
            except:
                pass
    return recent


def generate_quote(user_context: str, avoid_quotes: list = None) -> dict:
    """Generate a quote using Claude that matches the user's profile."""
    client = anthropic.Anthropic()

    avoid_section = ""
    if avoid_quotes:
        avoid_section = f"""

IMPORTANT: Do NOT use any of these quotes that were shown recently:
{chr(10).join(avoid_quotes)}

Choose a completely different quote from a different author if possible."""

    system_prompt = f"""You are a curator of wisdom. Your task is to provide a single compelling quote that will deeply resonate with the user based on their profile and intellectual influences.

The quote should:
- STRONGLY PREFER quotes from thinkers, authors, and figures the user admires or whose ideas they engage with (check their influences)
- Great sources include: philosophers they follow (e.g., Popper, rationalist thinkers), scientists, technologists, writers on topics they care about
- Connect to the user's values, current struggles, or intellectual interests
- Be thought-provoking and worthy of reflection
- Be concise (1-3 sentences max)
- Be a real, verifiable quote (not invented){avoid_section}

Respond with JSON only:
{{
    "quote": "The actual quote text",
    "author": "Author Name",
    "context": "One brief sentence on why this quote was chosen for this user"
}}"""

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
        recent_quotes = get_recent_quotes(days=365)
        quote_data = generate_quote(user_context, avoid_quotes=recent_quotes)
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
