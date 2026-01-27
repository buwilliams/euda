"""
Plugin Discovery - Scan and validate plugins.

Plugins are discovered by scanning the plugins/ directory for subdirectories
that contain a cli.py file with a main() function.
"""

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .exceptions import PluginNotFoundError, PluginValidationError


PLUGINS_DIR = Path(__file__).parent.parent.parent / "plugins"

# Cache for discovered plugins
_plugin_cache: Optional[List["PluginInfo"]] = None


@dataclass
class PluginInfo:
    """Information about a discovered plugin."""
    name: str
    path: Path
    description: str = ""

    def __str__(self) -> str:
        return f"{self.name}: {self.description}" if self.description else self.name


def _extract_plugin_description(cli_path: Path) -> str:
    """Extract description from a plugin's cli.py docstring.

    Args:
        cli_path: Path to the cli.py file

    Returns:
        First line of docstring or empty string
    """
    try:
        content = cli_path.read_text()
        # Look for module docstring
        if content.startswith('"""'):
            end = content.find('"""', 3)
            if end != -1:
                docstring = content[3:end].strip()
                # Return first line only
                return docstring.split("\n")[0].strip()
        elif content.startswith("'''"):
            end = content.find("'''", 3)
            if end != -1:
                docstring = content[3:end].strip()
                return docstring.split("\n")[0].strip()
    except Exception:
        pass
    return ""


def validate_plugin(name: str) -> bool:
    """Validate that a plugin exists and has the required structure.

    A valid plugin has:
    - A directory at plugins/{name}/
    - A cli.py file in that directory
    - A main() function in cli.py

    Args:
        name: Plugin name (directory name)

    Returns:
        True if valid, False otherwise
    """
    plugin_dir = PLUGINS_DIR / name
    cli_path = plugin_dir / "cli.py"

    if not plugin_dir.is_dir():
        return False

    if not cli_path.is_file():
        return False

    # Check for main() function
    try:
        content = cli_path.read_text()
        # Simple check - look for def main
        if "def main(" not in content:
            return False
    except Exception:
        return False

    return True


def discover_plugins() -> List[PluginInfo]:
    """Scan the plugins directory and return info about valid plugins.

    Returns:
        List of PluginInfo for each valid plugin found
    """
    global _plugin_cache

    if _plugin_cache is not None:
        return _plugin_cache

    plugins = []

    if not PLUGINS_DIR.is_dir():
        return plugins

    for item in sorted(PLUGINS_DIR.iterdir()):
        if item.is_dir() and not item.name.startswith(("_", ".")):
            if validate_plugin(item.name):
                cli_path = item / "cli.py"
                description = _extract_plugin_description(cli_path)
                plugins.append(PluginInfo(
                    name=item.name,
                    path=item,
                    description=description
                ))

    _plugin_cache = plugins
    return plugins


def get_plugin_info(name: str) -> PluginInfo:
    """Get information about a specific plugin.

    Args:
        name: Plugin name

    Returns:
        PluginInfo for the plugin

    Raises:
        PluginNotFoundError: If plugin doesn't exist
        PluginValidationError: If plugin is invalid
    """
    plugin_dir = PLUGINS_DIR / name

    if not plugin_dir.is_dir():
        raise PluginNotFoundError(f"Plugin not found: {name}")

    if not validate_plugin(name):
        raise PluginValidationError(f"Plugin {name} is invalid (missing cli.py or main())")

    cli_path = plugin_dir / "cli.py"
    description = _extract_plugin_description(cli_path)

    return PluginInfo(name=name, path=plugin_dir, description=description)


def invalidate_cache():
    """Clear the plugin discovery cache.

    Call this after adding or removing plugins to force rediscovery.
    """
    global _plugin_cache
    _plugin_cache = None


def get_plugin_path(name: str) -> Path:
    """Get the path to a plugin's directory.

    Args:
        name: Plugin name

    Returns:
        Path to plugin directory

    Raises:
        PluginNotFoundError: If plugin doesn't exist
    """
    plugin_dir = PLUGINS_DIR / name
    if not plugin_dir.is_dir():
        raise PluginNotFoundError(f"Plugin not found: {name}")
    return plugin_dir
