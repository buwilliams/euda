"""
Skill Usage - Extract help text and command information from skills.
"""

import re
from typing import List

from .executor import execute_skill
from .discovery import get_skill_info, discover_skills
from .exceptions import SkillNotFoundError


def get_skill_usage(name: str) -> str:
    """Get CLI help text for a skill.

    Args:
        name: Skill name

    Returns:
        Help text from running skill with --help
    """
    # First verify skill exists
    get_skill_info(name)

    # Run --help to get usage
    result = execute_skill(name, "--help", timeout=10)
    return result.output


def get_skill_commands(name: str) -> List[str]:
    """Parse available commands from skill help text.

    Args:
        name: Skill name

    Returns:
        List of command names available in the skill
    """
    help_text = get_skill_usage(name)

    # Parse Typer/Click style help output
    # Commands section usually looks like:
    #   Commands:
    #     command1  Description
    #     command2  Description
    commands = []

    in_commands_section = False
    for line in help_text.split("\n"):
        stripped = line.strip()

        if stripped.lower() == "commands:":
            in_commands_section = True
            continue

        if in_commands_section:
            # Empty line or new section ends commands
            if not stripped or (stripped and not stripped[0].isalnum()):
                if not stripped.startswith(" "):
                    in_commands_section = False
                    continue

            # Parse command name (first word)
            if stripped:
                parts = stripped.split()
                if parts and parts[0].replace("-", "").replace("_", "").isalnum():
                    commands.append(parts[0])

    return commands


def get_all_skills_summary() -> str:
    """Get a summary of all available skills.

    Returns:
        Formatted string listing all skills and their descriptions
    """
    skills = discover_skills()

    if not skills:
        return "No skills available."

    lines = ["Available skills:", ""]
    for skill in skills:
        if skill.description:
            lines.append(f"- **{skill.name}**: {skill.description}")
        else:
            lines.append(f"- **{skill.name}**")

    lines.append("")
    lines.append("Use skill_usage(skill) to see detailed help for a skill.")
    lines.append("Use execute_skill(skill, command) to run a command.")

    return "\n".join(lines)
