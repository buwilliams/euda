"""
Plugin Meta-Tools Tests.

Tests for the three meta-tools used by LLM agents.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestListPluginsTool:
    """Test list_plugins meta-tool."""

    def test_list_plugins_returns_all_plugins(self):
        """Should return all discovered plugins."""
        from src.plugins import list_plugins_tool

        result = list_plugins_tool()

        assert "plugins" in result
        assert "count" in result
        assert result["count"] > 0

        plugin_names = [p["name"] for p in result["plugins"]]
        assert "core" in plugin_names

    def test_list_plugins_includes_descriptions(self):
        """Should include plugin descriptions."""
        from src.plugins import list_plugins_tool

        result = list_plugins_tool()

        for plugin in result["plugins"]:
            assert "name" in plugin
            assert "description" in plugin

    def test_list_plugins_excludes_specified(self):
        """Should exclude plugins in excluded_plugins list."""
        from src.plugins import list_plugins_tool

        result = list_plugins_tool(excluded_plugins=["speech", "mastodon"])

        plugin_names = [p["name"] for p in result["plugins"]]
        assert "speech" not in plugin_names
        assert "mastodon" not in plugin_names
        assert "core" in plugin_names

    def test_list_plugins_includes_hint(self):
        """Should include usage hint."""
        from src.plugins import list_plugins_tool

        result = list_plugins_tool()

        assert "hint" in result
        assert "plugin_usage" in result["hint"]


class TestPluginUsageTool:
    """Test plugin_usage meta-tool."""

    def test_plugin_usage_returns_help(self):
        """Should return help text for plugin."""
        from src.plugins import plugin_usage_tool

        result = plugin_usage_tool("core")

        assert "plugin" in result
        assert "usage" in result
        assert result["plugin"] == "core"
        assert "topics" in result["usage"].lower()

    def test_plugin_usage_error_for_nonexistent(self):
        """Should return error for nonexistent plugin."""
        from src.plugins import plugin_usage_tool

        result = plugin_usage_tool("nonexistent_xyz")

        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_plugin_usage_handles_invalid_plugin(self, tmp_path):
        """Should return error for invalid plugin."""
        from src.plugins.tools import plugin_usage_tool

        # Create mock invalid plugin
        with patch('src.plugins.discovery.PLUGINS_DIR', tmp_path):
            result = plugin_usage_tool("nonexistent")

        assert "error" in result


class TestExecutePluginTool:
    """Test execute_plugin meta-tool."""

    def test_execute_plugin_runs_command(self):
        """Should execute plugin command and return result."""
        from src.plugins import execute_plugin_tool

        result = execute_plugin_tool("core", "dates current")

        assert "success" in result
        assert "output" in result
        assert "exit_code" in result
        assert result["success"] is True
        assert result["exit_code"] == 0

    def test_execute_plugin_returns_output(self):
        """Should return command output."""
        from src.plugins import execute_plugin_tool

        result = execute_plugin_tool("core", "dates current")

        assert "Date:" in result["output"]

    def test_execute_plugin_handles_failure(self):
        """Should handle command failures."""
        from src.plugins import execute_plugin_tool

        result = execute_plugin_tool("core", "nonexistent_command")

        assert result["success"] is False
        assert result["exit_code"] != 0

    def test_execute_plugin_error_for_nonexistent(self):
        """Should return error for nonexistent plugin."""
        from src.plugins import execute_plugin_tool

        result = execute_plugin_tool("nonexistent_xyz", "command")

        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_execute_plugin_passes_context(self):
        """Should pass agent context to execution."""
        from src.plugins.tools import execute_plugin_tool
        from src.plugins.executor import execute_plugin

        with patch('src.plugins.tools.execute_plugin') as mock_exec:
            mock_exec.return_value = MagicMock(
                success=True,
                output="test",
                exit_code=0
            )

            execute_plugin_tool(
                plugin="core",
                command="test",
                agent_id="agent-1",
                topic_id="topic-2",
                session_id="session-3"
            )

            mock_exec.assert_called_once()
            call_kwargs = mock_exec.call_args[1]
            assert call_kwargs.get("agent_id") == "agent-1"
            assert call_kwargs.get("topic_id") == "topic-2"
            assert call_kwargs.get("session_id") == "session-3"


class TestGetMetaTools:
    """Test meta-tool definitions for LLM."""

    def test_get_meta_tools_returns_three_tools(self):
        """Should return exactly three meta-tools."""
        from src.plugins import get_meta_tools

        tools = get_meta_tools()

        assert len(tools) == 3

    def test_get_meta_tools_has_correct_names(self):
        """Should have list_plugins, plugin_usage, execute_plugin."""
        from src.plugins import get_meta_tools

        tools = get_meta_tools()
        tool_names = [t["name"] for t in tools]

        assert "list_plugins" in tool_names
        assert "plugin_usage" in tool_names
        assert "execute_plugin" in tool_names

    def test_get_meta_tools_has_descriptions(self):
        """Should have descriptions for all tools."""
        from src.plugins import get_meta_tools

        tools = get_meta_tools()

        for tool in tools:
            assert "description" in tool
            assert tool["description"]

    def test_get_meta_tools_has_input_schemas(self):
        """Should have input schemas for all tools."""
        from src.plugins import get_meta_tools

        tools = get_meta_tools()

        for tool in tools:
            assert "input_schema" in tool
            assert "type" in tool["input_schema"]

    def test_execute_plugin_schema_requires_plugin_and_command(self):
        """execute_plugin should require plugin and command params."""
        from src.plugins import get_meta_tools

        tools = get_meta_tools()
        exec_tool = next(t for t in tools if t["name"] == "execute_plugin")

        schema = exec_tool["input_schema"]
        assert "plugin" in schema["required"]
        assert "command" in schema["required"]


class TestExecuteMetaTool:
    """Test the execute_meta_tool dispatcher."""

    def test_execute_meta_tool_list_plugins(self):
        """Should dispatch list_plugins correctly."""
        from src.plugins import execute_meta_tool

        result = execute_meta_tool("list_plugins", {})

        assert "plugins" in result
        assert "count" in result

    def test_execute_meta_tool_plugin_usage(self):
        """Should dispatch plugin_usage correctly."""
        from src.plugins import execute_meta_tool

        result = execute_meta_tool("plugin_usage", {"plugin": "core"})

        assert "usage" in result

    def test_execute_meta_tool_execute_plugin(self):
        """Should dispatch execute_plugin correctly."""
        from src.plugins import execute_meta_tool

        result = execute_meta_tool("execute_plugin", {
            "plugin": "core",
            "command": "dates current"
        })

        assert "success" in result
        assert "output" in result

    def test_execute_meta_tool_unknown_tool(self):
        """Should return error for unknown tool."""
        from src.plugins import execute_meta_tool

        result = execute_meta_tool("unknown_tool", {})

        assert "error" in result
        assert "Unknown" in result["error"]

    def test_execute_meta_tool_uses_context(self):
        """Should pass agent context from context dict."""
        from src.plugins import execute_meta_tool

        context = {
            "agent_id": "test-agent",
            "excluded_plugins": ["speech"]
        }

        result = execute_meta_tool("list_plugins", {}, agent_context=context)

        plugin_names = [p["name"] for p in result["plugins"]]
        assert "speech" not in plugin_names
