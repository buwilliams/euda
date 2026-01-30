"""
Prompt Templates - Load and render prompt templates.

System-level templates live in data/system/prompts/ and are always loaded first.
If an agent also has a template with the same filename in data/agents/{agent_id}/prompts/,
that content is appended to the system-level base.

For templates that only exist at the agent level, agent-only lookup applies.
Variables use Python format string syntax: {variable_name}
"""

from pathlib import Path
from typing import Dict, Optional

DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"
PROMPTS_DIR = DATA_DIR / "system" / "prompts"
AGENTS_DIR = DATA_DIR / "agents"

_template_cache: Dict[str, str] = {}


def load_template(name: str, agent_id: Optional[str] = None) -> str:
    """Load a prompt template by name.

    For templates that exist in data/system/prompts/, the system-level file is
    always loaded as the base. If the agent also has a file with the same name
    in data/agents/{agent_id}/prompts/, its content is appended.

    For templates that only exist at the agent level, agent-only lookup applies.

    Args:
        name: Template name/path without extension (e.g., 'agent/system' or 'reflection/append_system')
        agent_id: Optional agent ID to check for agent-specific templates

    Returns:
        Template content as string

    Raises:
        FileNotFoundError: If template doesn't exist
    """
    cache_key = f"{agent_id}:{name}" if agent_id else name

    if cache_key not in _template_cache:
        # Extract just the template filename from paths like "agent/system"
        template_filename = name.split("/")[-1] if "/" in name else name

        # Check system-level template
        system_path = PROMPTS_DIR / f"{template_filename}.md"
        system_content = system_path.read_text() if system_path.exists() else None

        # Check agent-level template
        agent_content = None
        if agent_id:
            agent_path = AGENTS_DIR / agent_id / "prompts" / f"{template_filename}.md"
            if agent_path.exists():
                agent_content = agent_path.read_text()

        # Combine: system base + agent append
        if system_content and agent_content:
            _template_cache[cache_key] = system_content + "\n\n" + agent_content
        elif system_content:
            _template_cache[cache_key] = system_content
        elif agent_content:
            _template_cache[cache_key] = agent_content
        else:
            raise FileNotFoundError(f"Template not found: {name}")

    return _template_cache[cache_key]


def render_template(name: str, agent_id: Optional[str] = None, **kwargs) -> str:
    """Load and render a template with variables.

    Args:
        name: Template name without extension
        agent_id: Optional agent ID to check for agent-specific overrides
                  (also passed to template as {agent_id} if present)
        **kwargs: Variables to substitute in the template

    Returns:
        Rendered template string
    """
    template = load_template(name, agent_id=agent_id)
    # Also pass agent_id to template kwargs so {agent_id} can be used in templates
    if agent_id is not None:
        kwargs.setdefault("agent_id", agent_id)
    return template.format(**kwargs)


def clear_cache():
    """Clear template cache (for development/testing)."""
    _template_cache.clear()
