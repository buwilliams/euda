"""
Plugin System - CLI-based plugin architecture for Euno.

This module provides infrastructure for discovering, validating, and executing
plugins that extend Euno's capabilities.

Plugins are CLI applications in the plugins/ directory. The LLM interacts with
them through three meta-tools: list_plugins, plugin_usage, and execute_plugin.

Public API:
- discover_plugins() - Find all valid plugins
- get_plugin_info(name) - Get info about a specific plugin
- execute_plugin(name, command) - Run a plugin command
- get_plugin_usage(name) - Get help text for a plugin
- get_meta_tools() - Get tool definitions for LLM
- execute_meta_tool(name, inputs) - Execute a meta-tool
"""

from .discovery import (
    discover_plugins,
    get_plugin_info,
    validate_plugin,
    invalidate_cache,
    PluginInfo,
)

from .executor import (
    execute_plugin,
    PluginResult,
)

from .usage import (
    get_plugin_usage,
    get_plugin_commands,
    get_all_plugins_summary,
)

from .tools import (
    get_meta_tools,
    execute_meta_tool,
    list_plugins_tool,
    plugin_usage_tool,
    execute_plugin_tool,
)

from .context import (
    build_plugin_env,
    get_data_dir_from_env,
    get_agent_id_from_env,
    get_topic_id_from_env,
    get_session_id_from_env,
)

from .exceptions import (
    PluginError,
    PluginNotFoundError,
    PluginExecutionError,
    PluginTimeoutError,
    PluginValidationError,
)

__all__ = [
    # Discovery
    "discover_plugins",
    "get_plugin_info",
    "validate_plugin",
    "invalidate_cache",
    "PluginInfo",
    # Execution
    "execute_plugin",
    "PluginResult",
    # Usage
    "get_plugin_usage",
    "get_plugin_commands",
    "get_all_plugins_summary",
    # Tools
    "get_meta_tools",
    "execute_meta_tool",
    "list_plugins_tool",
    "plugin_usage_tool",
    "execute_plugin_tool",
    # Context
    "build_plugin_env",
    "get_data_dir_from_env",
    "get_agent_id_from_env",
    "get_topic_id_from_env",
    "get_session_id_from_env",
    # Exceptions
    "PluginError",
    "PluginNotFoundError",
    "PluginExecutionError",
    "PluginTimeoutError",
    "PluginValidationError",
]
