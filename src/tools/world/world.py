"""
World tools for the World Agent (The Scout).

Tools for discovering opportunities in the external world that align with
user values while occasionally surprising with life-promoting novelty.
"""

from datetime import datetime
from pathlib import Path
import json

# Base paths - World agent directory
DATA_DIR = Path(__file__).parent.parent.parent / "data"
WORLD_DIR = DATA_DIR / "world"
OPPORTUNITIES_DIR = WORLD_DIR / "state" / "opportunities"

# Ensure directories exist
OPPORTUNITIES_DIR.mkdir(parents=True, exist_ok=True)


# ============== Opportunity Management ==============

def write_opportunity(
    title: str,
    description: str,
    category: str,
    alignment: str = "aligned",
    source: str = "",
    url: str = "",
    location: str = "",
    time_sensitive: bool = False,
    expires: str = "",
    tags: str = ""
) -> str:
    """
    Record a discovered opportunity.

    Args:
        title: Brief title of the opportunity
        description: What it is and why it might matter
        category: Type: event, person, place, learning, goal, other
        alignment: "aligned" (90%) or "expansive" (10% surprise)
        source: Where this was found
        url: Link if applicable
        location: Geographic relevance if any
        time_sensitive: Whether this has a deadline
        expires: ISO date when this opportunity expires
        tags: Comma-separated tags

    Returns:
        Confirmation message
    """
    timestamp = datetime.now().isoformat()

    opportunity = {
        "id": timestamp.replace(":", "-").replace(".", "-"),
        "created": timestamp,
        "title": title,
        "description": description,
        "category": category,
        "alignment": alignment,
        "source": source,
        "url": url,
        "location": location,
        "time_sensitive": time_sensitive,
        "expires": expires,
        "tags": [t.strip() for t in tags.split(",") if t.strip()],
        "status": "new",
        "surfaced": False,
        "user_response": None
    }

    # Save to category file
    category_file = OPPORTUNITIES_DIR / f"{category}.json"

    opportunities = []
    if category_file.exists():
        with open(category_file, 'r') as f:
            opportunities = json.load(f)

    opportunities.append(opportunity)

    with open(category_file, 'w') as f:
        json.dump(opportunities, f, indent=2)

    return f"Opportunity recorded: {title}"


def get_opportunities(
    category: str = "",
    alignment: str = "",
    include_surfaced: bool = False
) -> str:
    """
    Get discovered opportunities.

    Args:
        category: Filter by category (empty for all)
        alignment: Filter by "aligned" or "expansive"
        include_surfaced: Include already-surfaced opportunities

    Returns:
        List of opportunities
    """
    all_opportunities = []

    # Get categories to search
    if category:
        categories = [category]
    else:
        categories = ["event", "person", "place", "learning", "goal", "other"]

    for cat in categories:
        cat_file = OPPORTUNITIES_DIR / f"{cat}.json"
        if cat_file.exists():
            with open(cat_file, 'r') as f:
                opps = json.load(f)
            for opp in opps:
                opp["_category"] = cat
                all_opportunities.append(opp)

    # Filter
    filtered = []
    for opp in all_opportunities:
        if not include_surfaced and opp.get("surfaced"):
            continue
        if alignment and opp.get("alignment") != alignment:
            continue
        filtered.append(opp)

    if not filtered:
        return "No opportunities found matching criteria."

    # Sort by date, newest first
    filtered.sort(key=lambda x: x.get("created", ""), reverse=True)

    # Format output
    output = f"## Discovered Opportunities ({len(filtered)} found)\n\n"

    for opp in filtered[:20]:  # Limit to 20
        align_marker = "✨" if opp.get("alignment") == "expansive" else "→"
        output += f"{align_marker} **{opp['title']}** [{opp.get('_category', 'unknown')}]\n"
        output += f"   {opp['description'][:100]}...\n"
        if opp.get("url"):
            output += f"   Link: {opp['url']}\n"
        if opp.get("time_sensitive"):
            output += f"   ⏰ Time-sensitive"
            if opp.get("expires"):
                output += f" (expires: {opp['expires']})"
            output += "\n"
        output += "\n"

    return output


def mark_opportunity_surfaced(opportunity_id: str, user_response: str = "") -> str:
    """
    Mark an opportunity as surfaced to user.

    Args:
        opportunity_id: The opportunity ID
        user_response: Optional user response (interested, not interested, etc.)

    Returns:
        Confirmation message
    """
    for cat in ["event", "person", "place", "learning", "goal", "other"]:
        cat_file = OPPORTUNITIES_DIR / f"{cat}.json"
        if not cat_file.exists():
            continue

        with open(cat_file, 'r') as f:
            opportunities = json.load(f)

        for opp in opportunities:
            if opp.get("id") == opportunity_id:
                opp["surfaced"] = True
                opp["surfaced_at"] = datetime.now().isoformat()
                if user_response:
                    opp["user_response"] = user_response

                with open(cat_file, 'w') as f:
                    json.dump(opportunities, f, indent=2)

                return f"Marked as surfaced: {opp['title']}"

    return f"Opportunity not found: {opportunity_id}"


# ============== Discovery Helpers ==============

def get_discovery_context() -> str:
    """
    Get context for opportunity discovery.

    Returns:
        Current values and constraints for discovery
    """
    from ..values.values import get_current_values, get_phase_values

    current = get_current_values()
    phase = get_phase_values()

    output = """## Discovery Context

### Current Values
"""
    output += current if not current.startswith("No current") else "Not yet defined.\n"

    output += "\n### Life Phase Values\n"
    output += phase if not phase.startswith("No phase") else "Not yet defined.\n"

    output += """
### Discovery Guidelines

**90% Aligned**: Opportunities that clearly match stated values
- Directly supports current priorities
- Fits within known interests
- Low friction to pursue

**10% Expansive**: Life-promoting surprises
- Plausibly good for growth
- Outside the usual scope
- Might reveal unknown interests
- Still respects core values

**Privacy**: Only use public information unless value cards have been exchanged.

**Balance**: Mix practical with aspirational. Some opportunities should be easy wins,
others should stretch.
"""

    return output


def search_prompt(query: str, category: str = "") -> str:
    """
    Generate a search prompt with context.

    This helps frame searches in terms of user values.

    Args:
        query: What to search for
        category: Optional category focus

    Returns:
        Contextualized search prompt
    """
    context = get_discovery_context()

    category_focus = ""
    if category:
        category_hints = {
            "event": "events, conferences, workshops, meetups, gatherings",
            "person": "people to meet, experts, mentors, collaborators, communities",
            "place": "places to visit, locations, venues, destinations",
            "learning": "courses, books, tutorials, skills, knowledge areas",
            "goal": "projects, challenges, achievements, milestones"
        }
        category_focus = f"\n\nFocus on: {category_hints.get(category, category)}"

    return f"""## Search Context

{context}

### Search Query
{query}
{category_focus}

### Instructions
Search with this context in mind. Look for both:
1. Direct matches to the query that align with values
2. Unexpected discoveries that might expand horizons

Remember: Popularity doesn't matter. Alignment with THIS user's values does.
"""


def suggest_discoveries() -> str:
    """
    Suggest what to search for based on current values.

    Returns:
        Suggested discovery directions
    """
    context = get_discovery_context()

    return f"""## Discovery Suggestions

{context}

### Based on current values, consider searching for:

**Events & Gatherings**
- What events align with current projects and interests?
- What communities gather around these topics?

**People & Connections**
- Who is doing interesting work in aligned areas?
- What communities might offer meaningful connection?

**Places & Experiences**
- What locations support current values and interests?
- What experiences might shift perspective?

**Learning & Growth**
- What skills would amplify current work?
- What adjacent knowledge might open new possibilities?

**Goals & Projects**
- What challenges would be meaningful to pursue?
- What would stretch capacity in valuable directions?

### The 10% Question
What's something outside the usual scope that might be surprisingly good?
Something that sounds interesting but hasn't been explored yet?
"""


# Tool definitions for the LLM
WORLD_TOOLS = [
    {
        "name": "write_opportunity",
        "description": "Record a discovered opportunity. Use this when you find something that might interest the user.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Brief title of the opportunity"
                },
                "description": {
                    "type": "string",
                    "description": "What it is and why it might matter to this user"
                },
                "category": {
                    "type": "string",
                    "enum": ["event", "person", "place", "learning", "goal", "other"],
                    "description": "Type of opportunity"
                },
                "alignment": {
                    "type": "string",
                    "enum": ["aligned", "expansive"],
                    "description": "Whether this is aligned (90%) or expansive/surprising (10%)"
                },
                "source": {
                    "type": "string",
                    "description": "Where this was discovered"
                },
                "url": {
                    "type": "string",
                    "description": "Link if applicable"
                },
                "location": {
                    "type": "string",
                    "description": "Geographic relevance if any"
                },
                "time_sensitive": {
                    "type": "boolean",
                    "description": "Whether this has a deadline"
                },
                "expires": {
                    "type": "string",
                    "description": "ISO date when this expires"
                },
                "tags": {
                    "type": "string",
                    "description": "Comma-separated tags"
                }
            },
            "required": ["title", "description", "category"]
        }
    },
    {
        "name": "get_opportunities",
        "description": "Get discovered opportunities, optionally filtered by category or alignment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by category (empty for all)"
                },
                "alignment": {
                    "type": "string",
                    "enum": ["aligned", "expansive"],
                    "description": "Filter by alignment type"
                },
                "include_surfaced": {
                    "type": "boolean",
                    "description": "Include already-surfaced opportunities"
                }
            }
        }
    },
    {
        "name": "mark_opportunity_surfaced",
        "description": "Mark an opportunity as shown to user, with optional response.",
        "input_schema": {
            "type": "object",
            "properties": {
                "opportunity_id": {
                    "type": "string",
                    "description": "The opportunity ID"
                },
                "user_response": {
                    "type": "string",
                    "description": "User's response (interested, not interested, maybe later, etc.)"
                }
            },
            "required": ["opportunity_id"]
        }
    },
    {
        "name": "get_discovery_context",
        "description": "Get current values and guidelines for opportunity discovery.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "search_prompt",
        "description": "Generate a contextualized search prompt based on user values.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for"
                },
                "category": {
                    "type": "string",
                    "description": "Optional category focus"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "suggest_discoveries",
        "description": "Suggest what to search for based on current values.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

# Tool handlers mapping
WORLD_HANDLERS = {
    "write_opportunity": write_opportunity,
    "get_opportunities": get_opportunities,
    "mark_opportunity_surfaced": mark_opportunity_surfaced,
    "get_discovery_context": get_discovery_context,
    "search_prompt": search_prompt,
    "suggest_discoveries": suggest_discoveries,
}


# Test
if __name__ == "__main__":
    print(suggest_discoveries())
