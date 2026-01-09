"""
Prompt Templates - Load and render prompt templates.

Templates are stored in data/system/prompts/ as markdown files.
Variables use Python format string syntax: {variable_name}
"""

from pathlib import Path
from typing import Dict

PROMPTS_DIR = Path(__file__).parent.parent / "data" / "system" / "prompts"

_template_cache: Dict[str, str] = {}


def load_template(name: str) -> str:
    """Load a prompt template by name.

    Args:
        name: Template name without extension (e.g., 'system_prompt')

    Returns:
        Template content as string

    Raises:
        FileNotFoundError: If template doesn't exist
    """
    if name not in _template_cache:
        path = PROMPTS_DIR / f"{name}.md"
        if path.exists():
            _template_cache[name] = path.read_text()
        else:
            raise FileNotFoundError(f"Template not found: {name}")
    return _template_cache[name]


def render_template(name: str, **kwargs) -> str:
    """Load and render a template with variables.

    Args:
        name: Template name without extension
        **kwargs: Variables to substitute in the template

    Returns:
        Rendered template string
    """
    template = load_template(name)
    return template.format(**kwargs)


def clear_cache():
    """Clear template cache (for development/testing)."""
    _template_cache.clear()
