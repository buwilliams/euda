"""
Prompt Management - CRUD operations for agent prompt templates.

Allows agents to customize their prompts by creating agent-specific overrides.
System prompts are in data/system/prompts/, overrides in data/agents/{agent_id}/prompts/.
"""

from pathlib import Path
from typing import Optional, List, Dict

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
SYSTEM_PROMPTS_DIR = DATA_DIR / "system" / "prompts"
AGENTS_DIR = DATA_DIR / "agents"

# Available prompts that can be customized
AVAILABLE_PROMPTS = {
    # Agent prompts
    "system": "agent/system.md",
    "topic": "agent/topic.md",
    "topic_assignment": "agent/topic_assignment.md",
    "continue": "agent/continue.md",
    "continue_with_context": "agent/continue_with_context.md",
    "progress_check": "agent/progress_check.md",
    "consolidation": "agent/consolidation.md",
    # Consolidation prompts
    "append_system": "consolidation/append_system.md",
    "consolidate_system_agent": "consolidation/consolidate_system_agent.md",
    "consolidate_system_user": "consolidation/consolidate_system_user.md",
    "append_user": "consolidation/append_user.md",
    "consolidate_user": "consolidation/consolidate_user.md",
}


def list_prompts(agent_id: Optional[str] = None) -> List[Dict]:
    """List available prompts with their override status.

    Args:
        agent_id: Optional agent ID to check for agent-specific overrides

    Returns:
        List of dicts with name, description, has_override, and paths
    """
    prompts = []

    for name, rel_path in AVAILABLE_PROMPTS.items():
        system_path = SYSTEM_PROMPTS_DIR / rel_path
        override_path = None
        has_override = False

        if agent_id:
            # Check for agent override (just the filename, not the subdirectory)
            filename = Path(rel_path).name
            override_path = AGENTS_DIR / agent_id / "prompts" / filename
            has_override = override_path.exists()

        prompts.append({
            "name": name,
            "system_path": str(system_path.relative_to(DATA_DIR)) if system_path.exists() else None,
            "override_path": str(override_path.relative_to(DATA_DIR)) if override_path else None,
            "has_override": has_override,
            "exists": system_path.exists(),
        })

    return prompts


def get_prompt(agent_id: str, name: str) -> Dict:
    """Get a prompt's content, checking for agent override first.

    Args:
        agent_id: Agent ID to check for override
        name: Prompt name (e.g., 'system', 'topic_assignment')

    Returns:
        Dict with content, source ('override' or 'system'), and path
    """
    if name not in AVAILABLE_PROMPTS:
        return {"error": f"Unknown prompt: {name}. Available: {', '.join(AVAILABLE_PROMPTS.keys())}"}

    rel_path = AVAILABLE_PROMPTS[name]
    filename = Path(rel_path).name

    # Check agent override first
    override_path = AGENTS_DIR / agent_id / "prompts" / filename
    if override_path.exists():
        return {
            "name": name,
            "content": override_path.read_text(),
            "source": "override",
            "path": str(override_path.relative_to(DATA_DIR)),
        }

    # Fall back to system prompt
    system_path = SYSTEM_PROMPTS_DIR / rel_path
    if system_path.exists():
        return {
            "name": name,
            "content": system_path.read_text(),
            "source": "system",
            "path": str(system_path.relative_to(DATA_DIR)),
        }

    return {"error": f"Prompt not found: {name}"}


def update_prompt(agent_id: str, name: str, content: str) -> Dict:
    """Create or update an agent-specific prompt override.

    Args:
        agent_id: Agent ID to create override for
        name: Prompt name
        content: New prompt content

    Returns:
        Dict with status, path, and previous content (if any)
    """
    if name not in AVAILABLE_PROMPTS:
        return {"error": f"Unknown prompt: {name}. Available: {', '.join(AVAILABLE_PROMPTS.keys())}"}

    rel_path = AVAILABLE_PROMPTS[name]
    filename = Path(rel_path).name

    # Ensure prompts directory exists
    prompts_dir = AGENTS_DIR / agent_id / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    override_path = prompts_dir / filename

    # Store previous content if exists
    previous = override_path.read_text() if override_path.exists() else None

    # Write new content
    override_path.write_text(content)

    # Clear the prompt cache so changes take effect immediately
    _clear_prompt_cache()

    return {
        "status": "updated",
        "name": name,
        "path": str(override_path.relative_to(DATA_DIR)),
        "previous": previous,
    }


def reset_prompt(agent_id: str, name: str) -> Dict:
    """Remove an agent-specific prompt override, reverting to system default.

    Args:
        agent_id: Agent ID
        name: Prompt name to reset

    Returns:
        Dict with status and whether an override was removed
    """
    if name not in AVAILABLE_PROMPTS:
        return {"error": f"Unknown prompt: {name}. Available: {', '.join(AVAILABLE_PROMPTS.keys())}"}

    rel_path = AVAILABLE_PROMPTS[name]
    filename = Path(rel_path).name

    override_path = AGENTS_DIR / agent_id / "prompts" / filename

    if override_path.exists():
        content = override_path.read_text()
        override_path.unlink()

        # Clear the prompt cache so changes take effect immediately
        _clear_prompt_cache()

        return {
            "status": "reset",
            "name": name,
            "removed_override": True,
            "previous_content": content,
        }

    return {
        "status": "no_change",
        "name": name,
        "removed_override": False,
        "message": "No override exists for this prompt",
    }


def _clear_prompt_cache():
    """Clear the prompt template cache for immediate effect."""
    try:
        from src.agent.cognition.reasoning.prompts import clear_cache
        clear_cache()
    except ImportError:
        pass
