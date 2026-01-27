"""
Plugin Usage - Extract help text and command information from plugins.
"""

import re
from typing import List

from .executor import execute_plugin
from .discovery import get_plugin_info, discover_plugins
from .exceptions import PluginNotFoundError


def get_plugin_usage(name: str) -> str:
    """Get CLI help text for a plugin.

    Args:
        name: Plugin name

    Returns:
        Help text from running plugin with --help
    """
    # First verify plugin exists
    get_plugin_info(name)

    # Run --help to get usage
    result = execute_plugin(name, "--help", timeout=10)
    return result.output


def get_plugin_commands(name: str) -> List[str]:
    """Parse available commands from plugin help text.

    Args:
        name: Plugin name

    Returns:
        List of command names available in the plugin
    """
    help_text = get_plugin_usage(name)

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


def get_all_plugins_summary() -> str:
    """Get a summary of all available plugins.

    Returns:
        Formatted string listing all plugins and their descriptions
    """
    plugins = discover_plugins()

    if not plugins:
        return "No plugins available."

    lines = ["Available plugins:", ""]
    for plugin in plugins:
        if plugin.description:
            lines.append(f"- **{plugin.name}**: {plugin.description}")
        else:
            lines.append(f"- **{plugin.name}**")

    lines.append("")
    lines.append("Use plugin_usage(plugin) to see detailed help for a plugin.")
    lines.append("Use execute_plugin(plugin, command) to run a command.")

    return "\n".join(lines)
