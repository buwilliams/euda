"""
Epistemic tools for the Synthesis Agent (The Keeper).

Epistemic axioms are the FOUNDATIONAL layer - the beliefs that generate values.

Each epistemic entry includes PROVENANCE: the behavior/scenario that revealed
the belief, so the user can trace "how did the system conclude I believe this?"

Format for each entry:
- Behavior/Scenario: What was observed
- Epistemic Value: The underlying belief revealed
- Reasoning: How the behavior reveals this belief

Tools for reading and managing:
- Axioms: Core beliefs that drive decisions
- Mental Models: Frameworks used for thinking
- Epistemic Tools: Reasoning methods employed
"""

from datetime import datetime
from pathlib import Path

# Base paths
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
SYNTHESIS_DIR = DATA_DIR / "synthesis"
EPISTEMIC_DIR = SYNTHESIS_DIR / "state" / "epistemic"

# Ensure directory exists
EPISTEMIC_DIR.mkdir(parents=True, exist_ok=True)


def get_axioms() -> str:
    """
    Read the epistemic axioms - foundational beliefs that drive decisions.

    Each axiom includes provenance: the behavior that revealed it.

    Returns:
        Axioms content or message if not found
    """
    axioms_file = EPISTEMIC_DIR / "axioms.md"

    if not axioms_file.exists():
        return "No epistemic axioms derived yet."

    with open(axioms_file, 'r') as f:
        return f.read()


def write_axioms(content: str) -> str:
    """
    Write or update epistemic axioms.

    Format each axiom as:
    ### [Axiom Name]
    **Behavior**: What was observed that reveals this belief
    **Belief**: The underlying axiom
    **Reasoning**: How the behavior reveals this belief

    Args:
        content: The axioms content in markdown format with provenance

    Returns:
        Confirmation message
    """
    axioms_file = EPISTEMIC_DIR / "axioms.md"
    timestamp = datetime.now().isoformat()

    full_content = f"""# Epistemic Axioms

*The foundational beliefs that drive decisions and generate values*
*Each axiom includes the behavior that revealed it*

Updated: {timestamp}

{content}
"""

    with open(axioms_file, 'w') as f:
        f.write(full_content)

    return "Epistemic axioms updated"


def get_mental_models() -> str:
    """
    Read the mental models - frameworks used for thinking.

    Each model includes provenance: the behavior that revealed it.

    Returns:
        Mental models content or message if not found
    """
    models_file = EPISTEMIC_DIR / "mental_models.md"

    if not models_file.exists():
        return "No mental models derived yet."

    with open(models_file, 'r') as f:
        return f.read()


def write_mental_models(content: str) -> str:
    """
    Write or update mental models.

    Format each model as:
    ### [Model Name]
    **Behavior**: What was observed that reveals this framework
    **Model**: The underlying mental model
    **Reasoning**: How the behavior reveals this model

    Args:
        content: The mental models content in markdown format with provenance

    Returns:
        Confirmation message
    """
    models_file = EPISTEMIC_DIR / "mental_models.md"
    timestamp = datetime.now().isoformat()

    full_content = f"""# Mental Models

*The frameworks used for thinking and processing reality*
*Each model includes the behavior that revealed it*

Updated: {timestamp}

{content}
"""

    with open(models_file, 'w') as f:
        f.write(full_content)

    return "Mental models updated"


def get_epistemic_tools() -> str:
    """
    Read the epistemic tools - reasoning methods employed.

    Each tool includes provenance: the behavior that revealed it.

    Returns:
        Epistemic tools content or message if not found
    """
    tools_file = EPISTEMIC_DIR / "tools.md"

    if not tools_file.exists():
        return "No epistemic tools derived yet."

    with open(tools_file, 'r') as f:
        return f.read()


def write_epistemic_tools(content: str) -> str:
    """
    Write or update epistemic tools.

    Format each tool as:
    ### [Tool Name]
    **Behavior**: What was observed that reveals this reasoning method
    **Tool**: The epistemic tool/technique
    **Reasoning**: How the behavior reveals this tool

    Args:
        content: The epistemic tools content in markdown format with provenance

    Returns:
        Confirmation message
    """
    tools_file = EPISTEMIC_DIR / "tools.md"
    timestamp = datetime.now().isoformat()

    full_content = f"""# Epistemic Tools

*The reasoning methods and techniques employed*
*Each tool includes the behavior that revealed it*

Updated: {timestamp}

{content}
"""

    with open(tools_file, 'w') as f:
        f.write(full_content)

    return "Epistemic tools updated"


def get_all_epistemic() -> str:
    """
    Read all epistemic data (axioms, mental models, tools).

    Returns:
        All epistemic data concatenated with headers
    """
    sections = []

    axioms = get_axioms()
    if not axioms.startswith("No epistemic"):
        sections.append(axioms)

    models = get_mental_models()
    if not models.startswith("No mental"):
        sections.append(models)

    tools = get_epistemic_tools()
    if not tools.startswith("No epistemic"):
        sections.append(tools)

    if not sections:
        return "No epistemic data derived yet. Analyze summaries to uncover the mind behind behaviors."

    return "\n\n---\n\n".join(sections)


def note_epistemic_shift(
    domain: str,
    old_belief: str,
    new_belief: str,
    trigger: str
) -> str:
    """
    Record a shift in epistemic beliefs - when the user updates their thinking.

    Args:
        domain: What area this shift is in (e.g., "knowledge", "relationships", "agency")
        old_belief: The previous belief or framework
        new_belief: The new belief or framework
        trigger: What seems to have triggered this shift

    Returns:
        Confirmation message
    """
    shifts_file = EPISTEMIC_DIR / "shifts.md"
    timestamp = datetime.now().isoformat()

    entry = f"""
---

## Epistemic shift: {timestamp}

**Domain**: {domain}

**From**: {old_belief}

**To**: {new_belief}

**Trigger**: {trigger}

---
"""

    # Append to existing or create new
    if shifts_file.exists():
        with open(shifts_file, 'a') as f:
            f.write(entry)
    else:
        header = "# Epistemic Shifts\n\n*Evolution of foundational beliefs over time*\n"
        with open(shifts_file, 'w') as f:
            f.write(header + entry)

    return "Epistemic shift recorded"


def get_epistemic_shifts() -> str:
    """
    Read recorded epistemic shifts - how beliefs have evolved.

    Returns:
        Shifts content or message if none
    """
    shifts_file = EPISTEMIC_DIR / "shifts.md"

    if not shifts_file.exists():
        return "No epistemic shifts recorded yet."

    with open(shifts_file, 'r') as f:
        return f.read()


# Tool definitions for the LLM
EPISTEMIC_TOOLS = [
    {
        "name": "get_all_epistemic",
        "description": "Read all epistemic data (axioms, mental models, tools). Use this to understand the foundational beliefs that generate values.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_axioms",
        "description": "Read the epistemic axioms - the foundational beliefs that drive decisions and generate values.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "write_axioms",
        "description": "Write or update epistemic axioms. These are the core beliefs about reality that drive behavior.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The axioms in plain language markdown format"
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "get_mental_models",
        "description": "Read the mental models - frameworks used for thinking and processing reality.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "write_mental_models",
        "description": "Write or update mental models. These are the frameworks used for decisions, relationships, learning, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The mental models in plain language markdown format"
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "get_epistemic_tools",
        "description": "Read the epistemic tools - reasoning methods and techniques employed.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "write_epistemic_tools",
        "description": "Write or update epistemic tools. These are reasoning techniques like falsification, steel-manning, first principles, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The epistemic tools in plain language markdown format"
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "note_epistemic_shift",
        "description": "Record a shift in epistemic beliefs - when the user has updated their foundational thinking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "What area this shift is in (e.g., 'knowledge', 'relationships', 'agency')"
                },
                "old_belief": {
                    "type": "string",
                    "description": "The previous belief or framework"
                },
                "new_belief": {
                    "type": "string",
                    "description": "The new belief or framework"
                },
                "trigger": {
                    "type": "string",
                    "description": "What seems to have triggered this shift"
                }
            },
            "required": ["domain", "old_belief", "new_belief", "trigger"]
        }
    },
    {
        "name": "get_epistemic_shifts",
        "description": "Read recorded epistemic shifts - how foundational beliefs have evolved over time.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

# Tool handlers mapping
EPISTEMIC_HANDLERS = {
    "get_all_epistemic": get_all_epistemic,
    "get_axioms": get_axioms,
    "write_axioms": write_axioms,
    "get_mental_models": get_mental_models,
    "write_mental_models": write_mental_models,
    "get_epistemic_tools": get_epistemic_tools,
    "write_epistemic_tools": write_epistemic_tools,
    "note_epistemic_shift": note_epistemic_shift,
    "get_epistemic_shifts": get_epistemic_shifts,
}


# Test
if __name__ == "__main__":
    print(get_all_epistemic())
