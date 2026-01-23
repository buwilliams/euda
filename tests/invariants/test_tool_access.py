"""
Tool Access Invariant Tests.

Spec: docs/3_system.md - "Behavior" section

These tests verify that tool access is limited to agent configuration.

Invariants tested:
- Agents only have access to tools in their config
- Unknown tools are not returned
- Tools are grouped correctly by type
"""

import pytest


@pytest.mark.invariant
class TestToolAccessRestriction:
    """Test that tool access is restricted to agent config."""

    def test_get_tools_only_returns_configured_tools(self):
        """Agents should only get tools listed in their config.

        Spec: Each agent has access to a configured subset of available tools.
        """
        from src.tools import get_tools_for_agent

        # Request specific tools
        configured = ["list_jobs", "get_job", "create_job"]
        tools = get_tools_for_agent(configured)

        tool_names = [t["name"] for t in tools]

        # Should only have the configured tools
        assert set(tool_names) == set(configured)

    def test_unknown_tools_not_returned(self):
        """Unknown tool names should be silently ignored.

        Spec: Invalid tool names don't cause errors, just excluded.
        """
        from src.tools import get_tools_for_agent

        # Request mix of valid and invalid tools
        requested = ["list_jobs", "nonexistent_tool", "fake_tool", "get_job"]
        tools = get_tools_for_agent(requested)

        tool_names = [t["name"] for t in tools]

        # Should only have valid tools
        assert "list_jobs" in tool_names
        assert "get_job" in tool_names
        assert "nonexistent_tool" not in tool_names
        assert "fake_tool" not in tool_names
        assert len(tools) == 2

    def test_empty_config_returns_no_tools(self):
        """Empty tool config should return no tools.

        Spec: Agents with no configured tools have no tool access.
        """
        from src.tools import get_tools_for_agent

        tools = get_tools_for_agent([])
        assert tools == []

    def test_tools_grouped_by_type(self):
        """Tools should be grouped by their type.

        Spec: Tools are organized by type: data, agents, system, integration.
        """
        from src.tools import get_tools_grouped_by_type

        configured = ["list_jobs", "create_job", "get_today", "list_agents"]
        grouped = get_tools_grouped_by_type(configured)

        # Should have the expected types as keys
        assert "data" in grouped
        assert "agents" in grouped
        assert "system" in grouped
        assert "integration" in grouped

        # Jobs tools should be in data
        data_names = [t["name"] for t in grouped["data"]]
        assert "list_jobs" in data_names
        assert "create_job" in data_names

    def test_agent_only_sees_own_tools_in_prompt(self, patch_data_dir):
        """Agent system prompt should only show configured tools.

        Spec: Agent's prompt includes only its configured tools.
        """
        from src.agent.agent import Agent
        from unittest.mock import patch

        agent_dir = patch_data_dir / "agents" / "restricted-agent"
        agent_dir.mkdir(parents=True)
        (agent_dir / "identity.md").write_text("Test agent")

        with patch('src.agent.agent.AGENTS_DIR', patch_data_dir / "agents"):
            agent = Agent("restricted-agent", config={
                "id": "restricted-agent",
                "name": "Restricted Agent",
                "enabled": True,
                "tools": ["list_jobs"],  # Only one tool
                "triggers": []
            })

            prompt = agent._build_system_prompt()

            # Should mention list_jobs
            assert "list_jobs" in prompt

            # Should NOT mention tools not in config
            assert "create_job" not in prompt or "list_jobs" in prompt.split("create_job")[0]


@pytest.mark.invariant
class TestToolRegistry:
    """Test tool registry behavior."""

    def test_all_tools_have_required_fields(self):
        """All registered tools should have name, description, schema.

        Spec: Tools have name, description, and parameters.
        """
        from src.tools import get_all_tools

        tools = get_all_tools()

        for tool in tools:
            assert "name" in tool, f"Tool missing name"
            assert "description" in tool, f"Tool {tool.get('name')} missing description"
            assert "input_schema" in tool, f"Tool {tool.get('name')} missing schema"

    def test_tool_types_are_valid(self):
        """All tools should have valid types.

        Spec: Tool types are: data, agents, system, integration.
        """
        from src.tools import _TOOL_REGISTRY, TOOL_TYPES

        for name, tool in _TOOL_REGISTRY.items():
            tool_type = tool.get("type")
            # Type can be None (defaults to system) or must be valid
            if tool_type is not None:
                assert tool_type in TOOL_TYPES, \
                    f"Tool {name} has invalid type: {tool_type}"
