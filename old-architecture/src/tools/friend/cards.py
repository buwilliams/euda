"""
Value Cards tools for multi-agent negotiation.

Value cards represent a user's values in a shareable format:
- Internal card: Full detail, agent-managed
- Public card: User-approved, for sharing with others
- Received cards: Cards shared by other users/agents
"""

from datetime import datetime
from pathlib import Path
import json

# Base paths - Cards are owned by Friend agent
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
FRIEND_DIR = DATA_DIR / "friend"
CARDS_DIR = FRIEND_DIR / "state" / "cards"
RECEIVED_DIR = CARDS_DIR / "received"

# Ensure directories exist
CARDS_DIR.mkdir(parents=True, exist_ok=True)
RECEIVED_DIR.mkdir(parents=True, exist_ok=True)


# ============== Internal Card ==============

def get_internal_card() -> str:
    """
    Get the internal value card (full detail, agent-managed).

    Returns:
        Internal card content
    """
    card_file = CARDS_DIR / "internal.card.json"

    if not card_file.exists():
        return "No internal card exists yet. Generate one from current values."

    with open(card_file, 'r') as f:
        card = json.load(f)

    return json.dumps(card, indent=2)


def write_internal_card(
    core_values: list,
    current_priorities: list,
    interests: list,
    preferences: dict,
    boundaries: list = None
) -> str:
    """
    Write or update the internal value card.

    Args:
        core_values: List of core values (strings)
        current_priorities: What matters most right now
        interests: Topics, activities, areas of interest
        preferences: Dict of preferences (communication style, timing, etc.)
        boundaries: Things to avoid or respect

    Returns:
        Confirmation message
    """
    timestamp = datetime.now().isoformat()

    card = {
        "type": "internal",
        "updated": timestamp,
        "core_values": core_values,
        "current_priorities": current_priorities,
        "interests": interests,
        "preferences": preferences,
        "boundaries": boundaries or [],
        "version": 1
    }

    # Check for existing card to increment version
    card_file = CARDS_DIR / "internal.card.json"
    if card_file.exists():
        with open(card_file, 'r') as f:
            old_card = json.load(f)
        card["version"] = old_card.get("version", 0) + 1

    with open(card_file, 'w') as f:
        json.dump(card, f, indent=2)

    return f"Internal card updated (version {card['version']})"


# ============== Public Card ==============

def get_public_card() -> str:
    """
    Get the public value card (user-approved, for sharing).

    Returns:
        Public card content
    """
    card_file = CARDS_DIR / "public.card.json"

    if not card_file.exists():
        return "No public card exists yet. Create one from the internal card."

    with open(card_file, 'r') as f:
        card = json.load(f)

    return json.dumps(card, indent=2)


def write_public_card(
    display_name: str,
    values_summary: str,
    interests: list,
    open_to: list,
    not_interested: list = None,
    contact_preferences: dict = None
) -> str:
    """
    Write or update the public value card.

    Args:
        display_name: How to identify this person/agent
        values_summary: Brief description of core values
        interests: Topics open to discussing/exploring
        open_to: Types of connections welcome (collaboration, conversation, etc.)
        not_interested: Types of interactions to avoid
        contact_preferences: How/when to reach out

    Returns:
        Confirmation message
    """
    timestamp = datetime.now().isoformat()

    card = {
        "type": "public",
        "updated": timestamp,
        "display_name": display_name,
        "values_summary": values_summary,
        "interests": interests,
        "open_to": open_to,
        "not_interested": not_interested or [],
        "contact_preferences": contact_preferences or {},
        "version": 1
    }

    # Check for existing card to increment version
    card_file = CARDS_DIR / "public.card.json"
    if card_file.exists():
        with open(card_file, 'r') as f:
            old_card = json.load(f)
        card["version"] = old_card.get("version", 0) + 1

    with open(card_file, 'w') as f:
        json.dump(card, f, indent=2)

    return f"Public card updated (version {card['version']})"


def approve_public_card() -> str:
    """
    Mark the current public card as user-approved.

    Returns:
        Confirmation message
    """
    card_file = CARDS_DIR / "public.card.json"

    if not card_file.exists():
        return "No public card exists to approve."

    with open(card_file, 'r') as f:
        card = json.load(f)

    card["approved"] = True
    card["approved_at"] = datetime.now().isoformat()

    with open(card_file, 'w') as f:
        json.dump(card, f, indent=2)

    return "Public card approved for sharing"


# ============== Received Cards ==============

def receive_card(
    card_data: dict,
    from_agent: str,
    from_url: str = ""
) -> str:
    """
    Store a card received from another agent.

    Args:
        card_data: The card content
        from_agent: Identifier of sending agent
        from_url: URL of sending agent if available

    Returns:
        Confirmation message
    """
    timestamp = datetime.now().isoformat()

    received = {
        "received_at": timestamp,
        "from_agent": from_agent,
        "from_url": from_url,
        "card": card_data,
        "status": "new"  # new, reviewed, connected, declined
    }

    # Save with unique filename
    safe_name = from_agent.replace(" ", "_").replace("/", "_")[:50]
    card_file = RECEIVED_DIR / f"{safe_name}_{timestamp[:10]}.json"

    with open(card_file, 'w') as f:
        json.dump(received, f, indent=2)

    return f"Card received from {from_agent}"


def get_received_cards(status: str = "") -> str:
    """
    Get cards received from other agents.

    Args:
        status: Filter by status (new, reviewed, connected, declined)

    Returns:
        List of received cards
    """
    cards = []

    for card_file in RECEIVED_DIR.glob("*.json"):
        with open(card_file, 'r') as f:
            card = json.load(f)
        card["_file"] = card_file.name
        cards.append(card)

    # Filter by status if specified
    if status:
        cards = [c for c in cards if c.get("status") == status]

    if not cards:
        return "No received cards" + (f" with status '{status}'" if status else "") + "."

    # Sort by date, newest first
    cards.sort(key=lambda x: x.get("received_at", ""), reverse=True)

    output = f"## Received Cards ({len(cards)})\n\n"
    for card in cards:
        agent = card.get("from_agent", "Unknown")
        received = card.get("received_at", "")[:10]
        status_emoji = {
            "new": "🆕",
            "reviewed": "👀",
            "connected": "🤝",
            "declined": "❌"
        }.get(card.get("status"), "❓")

        output += f"{status_emoji} **{agent}** (received {received})\n"

        # Show card summary
        inner_card = card.get("card", {})
        if inner_card.get("values_summary"):
            output += f"   {inner_card['values_summary'][:100]}...\n"
        if inner_card.get("interests"):
            output += f"   Interests: {', '.join(inner_card['interests'][:5])}\n"
        output += "\n"

    return output


def update_received_card_status(from_agent: str, new_status: str) -> str:
    """
    Update the status of a received card.

    Args:
        from_agent: The agent identifier
        new_status: New status (reviewed, connected, declined)

    Returns:
        Confirmation message
    """
    for card_file in RECEIVED_DIR.glob("*.json"):
        with open(card_file, 'r') as f:
            card = json.load(f)

        if card.get("from_agent") == from_agent:
            card["status"] = new_status
            card["status_updated"] = datetime.now().isoformat()

            with open(card_file, 'w') as f:
                json.dump(card, f, indent=2)

            return f"Updated {from_agent}'s card status to '{new_status}'"

    return f"No card found from {from_agent}"


# ============== Card Generation ==============

def generate_cards_from_values() -> str:
    """
    Generate card drafts from profile.

    Returns:
        Status message with guidance
    """
    from ..profiler.profile import get_profile

    profile = get_profile()

    output = """## Card Generation Context

Use the profile below to generate both internal and public cards.

### Identity Profile
"""
    output += profile[:3000] if not profile.startswith("No identity") else "Not defined yet.\n"

    output += """

### Instructions

**For Internal Card** (write_internal_card):
- Include key identity constraints and behavioral patterns
- Be comprehensive about priorities and interests
- Include preferences and boundaries
- This is for agent use, not sharing

**For Public Card** (write_public_card):
- Summarize identity concisely
- Focus on what enables connection
- Be clear about what you're open to
- Respect privacy - only share what's comfortable
- This will be shared with others
"""

    return output


# Tool definitions for the LLM
CARDS_TOOLS = [
    {
        "name": "get_internal_card",
        "description": "Get the internal value card (full detail, agent-managed).",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "write_internal_card",
        "description": "Write or update the internal value card with full detail.",
        "input_schema": {
            "type": "object",
            "properties": {
                "core_values": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of core values"
                },
                "current_priorities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "What matters most right now"
                },
                "interests": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Topics, activities, areas of interest"
                },
                "preferences": {
                    "type": "object",
                    "description": "Preferences (communication style, timing, etc.)"
                },
                "boundaries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Things to avoid or respect"
                }
            },
            "required": ["core_values", "current_priorities", "interests", "preferences"]
        }
    },
    {
        "name": "get_public_card",
        "description": "Get the public value card (user-approved, for sharing).",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "write_public_card",
        "description": "Write or update the public value card for sharing with others.",
        "input_schema": {
            "type": "object",
            "properties": {
                "display_name": {
                    "type": "string",
                    "description": "How to identify this person/agent"
                },
                "values_summary": {
                    "type": "string",
                    "description": "Brief description of core values"
                },
                "interests": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Topics open to discussing/exploring"
                },
                "open_to": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Types of connections welcome"
                },
                "not_interested": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Types of interactions to avoid"
                },
                "contact_preferences": {
                    "type": "object",
                    "description": "How/when to reach out"
                }
            },
            "required": ["display_name", "values_summary", "interests", "open_to"]
        }
    },
    {
        "name": "approve_public_card",
        "description": "Mark the current public card as user-approved for sharing.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "receive_card",
        "description": "Store a card received from another agent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "card_data": {
                    "type": "object",
                    "description": "The card content"
                },
                "from_agent": {
                    "type": "string",
                    "description": "Identifier of sending agent"
                },
                "from_url": {
                    "type": "string",
                    "description": "URL of sending agent if available"
                }
            },
            "required": ["card_data", "from_agent"]
        }
    },
    {
        "name": "get_received_cards",
        "description": "Get cards received from other agents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["new", "reviewed", "connected", "declined"],
                    "description": "Filter by status"
                }
            }
        }
    },
    {
        "name": "update_received_card_status",
        "description": "Update the status of a received card.",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_agent": {
                    "type": "string",
                    "description": "The agent identifier"
                },
                "new_status": {
                    "type": "string",
                    "enum": ["reviewed", "connected", "declined"],
                    "description": "New status"
                }
            },
            "required": ["from_agent", "new_status"]
        }
    },
    {
        "name": "generate_cards_from_values",
        "description": "Get current values context to help generate cards.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

# Tool handlers mapping
CARDS_HANDLERS = {
    "get_internal_card": get_internal_card,
    "write_internal_card": write_internal_card,
    "get_public_card": get_public_card,
    "write_public_card": write_public_card,
    "approve_public_card": approve_public_card,
    "receive_card": receive_card,
    "get_received_cards": get_received_cards,
    "update_received_card_status": update_received_card_status,
    "generate_cards_from_values": generate_cards_from_values,
}


# Test
if __name__ == "__main__":
    print(generate_cards_from_values())
