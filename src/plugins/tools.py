"""
Plugin Tools - Meta-tools for LLM to interact with plugins.

These three tools replace 82+ specialized tools with a plugin-based approach.
The LLM uses these to discover, understand, and execute plugin commands.
"""

from typing import List, Optional

from .discovery import discover_plugins, get_plugin_info
from .executor import execute_plugin, PluginResult
from .usage import get_plugin_usage, get_all_plugins_summary
from .exceptions import PluginError, PluginNotFoundError


# Tool type for all meta-tools
TOOL_TYPE = "system"


def list_plugins_tool(excluded_plugins: Optional[List[str]] = None) -> dict:
    """List all available plugins.

    Args:
        excluded_plugins: List of plugin names to exclude from results

    Returns:
        Dict with plugins list and summary
    """
    plugins = discover_plugins()

    # Filter excluded plugins
    if excluded_plugins:
        plugins = [p for p in plugins if p.name not in excluded_plugins]

    plugin_list = []
    for plugin in plugins:
        plugin_list.append({
            "name": plugin.name,
            "description": plugin.description or "(no description)"
        })

    return {
        "plugins": plugin_list,
        "count": len(plugin_list),
        "hint": "Use plugin_usage(name) to see commands for a plugin"
    }


def plugin_usage_tool(plugin: str) -> dict:
    """Get CLI help for a plugin.

    Args:
        plugin: Plugin name

    Returns:
        Dict with usage text or error
    """
    try:
        usage = get_plugin_usage(plugin)
        return {
            "plugin": plugin,
            "usage": usage
        }
    except PluginNotFoundError:
        return {"error": f"Plugin not found: {plugin}"}
    except PluginError as e:
        return {"error": str(e)}


def execute_plugin_tool(
    plugin: str,
    command: str,
    agent_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> dict:
    """Execute a plugin command.

    Args:
        plugin: Plugin name
        command: Command string (e.g., "topics list --status todo")
        agent_id: Current agent ID (optional, for context)
        topic_id: Current topic ID (optional, for context)
        session_id: Current session ID (optional, for context)

    Returns:
        Dict with success status, output, and exit code
    """
    try:
        result = execute_plugin(
            plugin,
            command,
            timeout=60,
            agent_id=agent_id,
            topic_id=topic_id,
            session_id=session_id
        )

        return {
            "success": result.success,
            "output": result.output,
            "exit_code": result.exit_code
        }
    except PluginNotFoundError:
        return {"error": f"Plugin not found: {plugin}"}
    except PluginError as e:
        return {"error": str(e)}


def get_meta_tools() -> list:
    """Get the three meta-tool definitions for LLM use.

    Returns:
        List of tool definitions in Claude tool format
    """
    return [
        {
            "name": "list_plugins",
            "description": "List all available plugins. Use to discover what capabilities are available.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "plugin_usage",
            "description": "Get CLI help for a plugin. Shows available commands and their arguments. Use before executing an unfamiliar plugin.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "plugin": {
                        "type": "string",
                        "description": "Plugin name (e.g., 'core', 'nextcloud')"
                    }
                },
                "required": ["plugin"]
            }
        },
        {
            "name": "execute_plugin",
            "description": "Execute a plugin command. Run plugin commands to perform actions like managing topics, memory, or external integrations.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "plugin": {
                        "type": "string",
                        "description": "Plugin name (e.g., 'core', 'nextcloud')"
                    },
                    "command": {
                        "type": "string",
                        "description": "Command string including subcommands and arguments (e.g., 'topics list --status todo')"
                    }
                },
                "required": ["plugin", "command"]
            }
        }
    ]


def execute_meta_tool(name: str, inputs: dict, agent_context: dict = None) -> dict:
    """Execute a meta-tool by name.

    Args:
        name: Tool name (list_plugins, plugin_usage, execute_plugin)
        inputs: Tool inputs
        agent_context: Optional context with agent_id, topic_id, session_id

    Returns:
        Tool result dict
    """
    context = agent_context or {}

    if name == "list_plugins":
        excluded = context.get("excluded_plugins", [])
        return list_plugins_tool(excluded_plugins=excluded)

    elif name == "plugin_usage":
        return plugin_usage_tool(inputs.get("plugin", ""))

    elif name == "execute_plugin":
        return execute_plugin_tool(
            plugin=inputs.get("plugin", ""),
            command=inputs.get("command", ""),
            agent_id=context.get("agent_id"),
            topic_id=context.get("topic_id"),
            session_id=context.get("session_id")
        )

    else:
        return {"error": f"Unknown meta-tool: {name}"}
