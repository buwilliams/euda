"""
Prompt Management - CRUD operations for agent prompt templates.

Prompts live in agent-level directories: data/agents/{agent_id}/prompts/.
There are no system-level defaults — each agent owns its own prompts.
"""

from pathlib import Path
from typing import Optional, List, Dict

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"

# Available prompts that can be customized per-agent
AVAILABLE_PROMPTS = {
    # Agent prompts
    "system": "system.md",
    "topic": "topic.md",
    "topic_assignment": "topic_assignment.md",
    "continue": "continue.md",
    "continue_with_context": "continue_with_context.md",
    "progress_check": "progress_check.md",
    "consolidation": "consolidation.md",
    # Consolidation prompts
    "append_system": "append_system.md",
    "append_user": "append_user.md",
    "append_batch_user": "append_batch_user.md",
    "consolidate_system_agent": "consolidate_system_agent.md",
    "consolidate_system_user": "consolidate_system_user.md",
    "consolidate_user": "consolidate_user.md",
    # Upload prompts
    "extract_memories": "extract_memories.md",
}


def list_prompts(agent_id: Optional[str] = None) -> List[Dict]:
    """List available prompts with their status for an agent.

    Args:
        agent_id: Optional agent ID to check for agent-specific prompts

    Returns:
        List of dicts with name, path, and exists status
    """
    prompts = []

    for name, filename in AVAILABLE_PROMPTS.items():
        prompt_path = None
        exists = False

        if agent_id:
            prompt_path = AGENTS_DIR / agent_id / "prompts" / filename
            exists = prompt_path.exists()

        prompts.append({
            "name": name,
            "path": str(prompt_path.relative_to(DATA_DIR)) if prompt_path else None,
            "exists": exists,
        })

    return prompts


def get_prompt(agent_id: str, name: str) -> Dict:
    """Get a prompt's content from the agent's prompts directory.

    Args:
        agent_id: Agent ID
        name: Prompt name (e.g., 'system', 'topic_assignment')

    Returns:
        Dict with content, source, and path
    """
    if name not in AVAILABLE_PROMPTS:
        return {"error": f"Unknown prompt: {name}. Available: {', '.join(AVAILABLE_PROMPTS.keys())}"}

    filename = AVAILABLE_PROMPTS[name]
    prompt_path = AGENTS_DIR / agent_id / "prompts" / filename

    if prompt_path.exists():
        return {
            "name": name,
            "content": prompt_path.read_text(),
            "source": "agent",
            "path": str(prompt_path.relative_to(DATA_DIR)),
        }

    return {"error": f"Prompt not found: {name} for agent {agent_id}"}


def update_prompt(agent_id: str, name: str, content: str) -> Dict:
    """Create or update an agent's prompt.

    Args:
        agent_id: Agent ID
        name: Prompt name
        content: New prompt content

    Returns:
        Dict with status, path, and previous content (if any)
    """
    if name not in AVAILABLE_PROMPTS:
        return {"error": f"Unknown prompt: {name}. Available: {', '.join(AVAILABLE_PROMPTS.keys())}"}

    filename = AVAILABLE_PROMPTS[name]

    # Ensure prompts directory exists
    prompts_dir = AGENTS_DIR / agent_id / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    prompt_path = prompts_dir / filename

    # Store previous content if exists
    previous = prompt_path.read_text() if prompt_path.exists() else None

    # Write new content
    prompt_path.write_text(content)

    # Clear the prompt cache so changes take effect immediately
    _clear_prompt_cache()

    return {
        "status": "updated",
        "name": name,
        "path": str(prompt_path.relative_to(DATA_DIR)),
        "previous": previous,
    }


def reset_prompt(agent_id: str, name: str) -> Dict:
    """Reset is not supported — prompts are agent-owned with no system defaults.

    Args:
        agent_id: Agent ID
        name: Prompt name

    Returns:
        Dict with error message
    """
    if name not in AVAILABLE_PROMPTS:
        return {"error": f"Unknown prompt: {name}. Available: {', '.join(AVAILABLE_PROMPTS.keys())}"}

    return {
        "status": "no_change",
        "name": name,
        "message": "Prompts are agent-owned. There are no system defaults to reset to. Edit the prompt directly with update_prompt.",
    }


def _clear_prompt_cache():
    """Clear the prompt template cache for immediate effect."""
    try:
        from src.agent.cognition.reasoning.prompts import clear_cache
        clear_cache()
    except ImportError:
        pass
