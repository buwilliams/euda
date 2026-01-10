"""
Prompt Templates - Load and render prompt templates.

Templates are stored in data/system/prompts/ as markdown files.
Agent-specific overrides can be placed in data/agents/{agent_id}/prompts/
Variables use Python format string syntax: {variable_name}
"""

from pathlib import Path
from typing import Dict, Optional

DATA_DIR = Path(__file__).parent.parent / "data"
PROMPTS_DIR = DATA_DIR / "system" / "prompts"
AGENTS_DIR = DATA_DIR / "agents"

_template_cache: Dict[str, str] = {}


def load_template(name: str, agent_id: Optional[str] = None) -> str:
    """Load a prompt template by name, checking agent-specific overrides first.

    Args:
        name: Template name/path without extension (e.g., 'agent/system' or 'synthesis/append_system')
        agent_id: Optional agent ID to check for agent-specific overrides

    Returns:
        Template content as string

    Raises:
        FileNotFoundError: If template doesn't exist
    """
    # Create cache key that includes agent_id for agent-specific templates
    cache_key = f"{agent_id}:{name}" if agent_id else name

    if cache_key not in _template_cache:
        template_path = None

        # Check agent-specific prompts first
        if agent_id:
            # Extract just the template filename from paths like "agent/task_work"
            template_filename = name.split("/")[-1] if "/" in name else name
            agent_path = AGENTS_DIR / agent_id / "prompts" / f"{template_filename}.md"
            if agent_path.exists():
                template_path = agent_path

        # Fall back to system prompts
        if not template_path:
            system_path = PROMPTS_DIR / f"{name}.md"
            if system_path.exists():
                template_path = system_path

        if template_path:
            _template_cache[cache_key] = template_path.read_text()
        else:
            raise FileNotFoundError(f"Template not found: {name}")

    return _template_cache[cache_key]


def render_template(name: str, agent_id: Optional[str] = None, **kwargs) -> str:
    """Load and render a template with variables.

    Args:
        name: Template name without extension
        agent_id: Optional agent ID to check for agent-specific overrides
        **kwargs: Variables to substitute in the template

    Returns:
        Rendered template string
    """
    template = load_template(name, agent_id=agent_id)
    return template.format(**kwargs)


def clear_cache():
    """Clear template cache (for development/testing)."""
    _template_cache.clear()
