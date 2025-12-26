"""
Context tools for the Identity Agent (The Keeper).

Context provides SUPPORTING data - biographical facts and relationships.
These are data points that help agents anticipate the user, but do NOT define identity.
Values and beliefs remain the core of identity.
"""

from datetime import datetime
from pathlib import Path
import re

# Base paths
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
IDENTITY_DIR = DATA_DIR / "identity"
CONTEXT_DIR = IDENTITY_DIR / "context"

# Ensure directory exists
CONTEXT_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# BIOGRAPHICAL TOOLS
# =============================================================================

def get_biographical() -> str:
    """
    Read biographical context.

    Returns:
        Biographical content or message if not found
    """
    bio_file = CONTEXT_DIR / "biographical.md"

    if not bio_file.exists():
        return "No biographical context recorded yet."

    with open(bio_file, 'r') as f:
        return f.read()


def update_biographical(section: str, content: str) -> str:
    """
    Update a section of the biographical context.

    Args:
        section: The section to update (e.g., "Name", "Birth Date", "Background")
        content: The content for that section

    Returns:
        Confirmation message
    """
    bio_file = CONTEXT_DIR / "biographical.md"
    timestamp = datetime.now().isoformat()

    # Read existing content or create new
    if bio_file.exists():
        with open(bio_file, 'r') as f:
            existing = f.read()
    else:
        existing = f"""# Biographical Context

*Background information - supports but doesn't define identity*

Updated: {timestamp}

## Basic Information

- **Name**:
- **Birth Date**:
- **Birth Place**:
- **Current Location**:

## Background

(To be filled)

---

*Sources: manual entry, derived from log*
"""

    # Update the timestamp
    existing = re.sub(r'Updated: .*', f'Updated: {timestamp}', existing)

    # Try to update the specific field if it's a basic info field
    basic_fields = ["Name", "Birth Date", "Birth Place", "Current Location"]
    if section in basic_fields:
        pattern = rf'(\*\*{section}\*\*:).*'
        replacement = rf'\1 {content}'
        existing = re.sub(pattern, replacement, existing)
    elif section == "Background":
        # Replace the background section
        pattern = r'(## Background\n\n).*?(\n\n---|\Z)'
        replacement = rf'\1{content}\2'
        existing = re.sub(pattern, replacement, existing, flags=re.DOTALL)
    else:
        # Append as a new section before the sources line
        new_section = f"\n## {section}\n\n{content}\n"
        existing = existing.replace("\n---\n\n*Sources:", f"{new_section}\n---\n\n*Sources:")

    with open(bio_file, 'w') as f:
        f.write(existing)

    return f"Biographical context updated: {section}"


# =============================================================================
# RELATIONSHIPS TOOLS
# =============================================================================

def get_relationships() -> str:
    """
    Read all relationship narratives.

    Returns:
        Relationships content or message if not found
    """
    rel_file = CONTEXT_DIR / "relationships.md"

    if not rel_file.exists():
        return "No relationships recorded yet."

    with open(rel_file, 'r') as f:
        return f.read()


def get_relationship(name: str) -> str:
    """
    Read the narrative about a specific relationship.

    Args:
        name: The name of the person

    Returns:
        Relationship narrative or message if not found
    """
    rel_file = CONTEXT_DIR / "relationships.md"

    if not rel_file.exists():
        return f"No relationships recorded yet."

    with open(rel_file, 'r') as f:
        content = f.read()

    # Search for the person's section
    pattern = rf'###\s+(?:\w+:\s+)?{re.escape(name)}.*?(?=\n###|\n##|\Z)'
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

    if match:
        return match.group(0).strip()
    else:
        return f"No relationship found for: {name}"


def add_relationship(name: str, relationship_type: str, narrative: str) -> str:
    """
    Add a new relationship narrative.

    Args:
        name: The person's name
        relationship_type: Type of relationship (e.g., "Partner", "Mother", "Friend")
        narrative: The narrative description of the relationship

    Returns:
        Confirmation message
    """
    rel_file = CONTEXT_DIR / "relationships.md"
    timestamp = datetime.now().isoformat()

    # Read existing or create new
    if rel_file.exists():
        with open(rel_file, 'r') as f:
            existing = f.read()
    else:
        existing = f"""# Relationships

*People who matter - context for anticipation*

Updated: {timestamp}

## Family

## Close Friends

---

*Sources: conversations, log entries*
"""

    # Update timestamp
    existing = re.sub(r'Updated: .*', f'Updated: {timestamp}', existing)

    # Determine which section to add to
    family_types = ["Partner", "Mother", "Father", "Parent", "Sister", "Brother",
                    "Sibling", "Child", "Son", "Daughter", "Grandmother", "Grandfather",
                    "Grandparent", "Aunt", "Uncle", "Cousin", "Spouse", "Wife", "Husband"]

    new_entry = f"\n### {relationship_type}: {name}\n\n{narrative}\n"

    if relationship_type in family_types:
        # Add to Family section
        if "## Close Friends" in existing:
            existing = existing.replace("## Close Friends", f"{new_entry}\n## Close Friends")
        else:
            # Append before sources
            existing = existing.replace("\n---\n\n*Sources:", f"{new_entry}\n---\n\n*Sources:")
    else:
        # Add to Close Friends section
        if "\n---\n\n*Sources:" in existing:
            existing = existing.replace("\n---\n\n*Sources:", f"{new_entry}\n---\n\n*Sources:")
        else:
            existing += new_entry

    with open(rel_file, 'w') as f:
        f.write(existing)

    return f"Relationship added: {relationship_type} - {name}"


def update_relationship(name: str, narrative: str) -> str:
    """
    Update the narrative for an existing relationship.

    Args:
        name: The person's name
        narrative: The updated narrative

    Returns:
        Confirmation message
    """
    rel_file = CONTEXT_DIR / "relationships.md"
    timestamp = datetime.now().isoformat()

    if not rel_file.exists():
        return f"No relationships file exists. Use add_relationship instead."

    with open(rel_file, 'r') as f:
        content = f.read()

    # Update timestamp
    content = re.sub(r'Updated: .*', f'Updated: {timestamp}', content)

    # Find and replace the person's narrative
    pattern = rf'(###\s+\w+:\s+{re.escape(name)}\n\n).*?(?=\n###|\n##|\n---|\Z)'

    if re.search(pattern, content, re.DOTALL | re.IGNORECASE):
        content = re.sub(pattern, rf'\1{narrative}\n', content, flags=re.DOTALL | re.IGNORECASE)

        with open(rel_file, 'w') as f:
            f.write(content)

        return f"Relationship updated: {name}"
    else:
        return f"No existing relationship found for: {name}. Use add_relationship instead."


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

CONTEXT_TOOLS = [
    # Biographical tools
    {
        "name": "get_biographical",
        "description": "Read biographical context - background information about the user (name, birth date, etc.). This is supporting data, not core identity.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "update_biographical",
        "description": "Update a section of biographical context. Use when user shares facts about themselves.",
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "description": "Section to update: 'Name', 'Birth Date', 'Birth Place', 'Current Location', 'Background', or a new section name"
                },
                "content": {
                    "type": "string",
                    "description": "The content for that section"
                }
            },
            "required": ["section", "content"]
        }
    },
    # Relationship tools
    {
        "name": "get_relationships",
        "description": "Read all relationship narratives - the people who matter to the user. This is supporting context for anticipation.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_relationship",
        "description": "Read the narrative about a specific person in the user's life.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The person's name"
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "add_relationship",
        "description": "Add a new relationship. Use when user mentions someone important in their life.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The person's name"
                },
                "relationship_type": {
                    "type": "string",
                    "description": "Type: Partner, Mother, Father, Sister, Brother, Child, Friend, Colleague, etc."
                },
                "narrative": {
                    "type": "string",
                    "description": "Narrative description of this relationship"
                }
            },
            "required": ["name", "relationship_type", "narrative"]
        }
    },
    {
        "name": "update_relationship",
        "description": "Update the narrative for an existing relationship.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The person's name"
                },
                "narrative": {
                    "type": "string",
                    "description": "The updated narrative description"
                }
            },
            "required": ["name", "narrative"]
        }
    }
]

# Tool handlers mapping
CONTEXT_HANDLERS = {
    "get_biographical": get_biographical,
    "update_biographical": update_biographical,
    "get_relationships": get_relationships,
    "get_relationship": get_relationship,
    "add_relationship": add_relationship,
    "update_relationship": update_relationship,
}


# Test
if __name__ == "__main__":
    print("Biographical:")
    print(get_biographical())
    print("\nRelationships:")
    print(get_relationships())
