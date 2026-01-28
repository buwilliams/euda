"""
Skill Meta-Tools Tests.

Tests for the three meta-tools used by LLM agents.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestListSkillsTool:
    """Test list_skills meta-tool."""

    def test_list_skills_returns_all_skills(self):
        """Should return all discovered skills."""
        from src.skills import list_skills_tool

        result = list_skills_tool()

        assert "skills" in result
        assert "count" in result
        assert result["count"] > 0

        skill_names = [s["name"] for s in result["skills"]]
        assert "core" in skill_names

    def test_list_skills_includes_descriptions(self):
        """Should include skill descriptions."""
        from src.skills import list_skills_tool

        result = list_skills_tool()

        for skill in result["skills"]:
            assert "name" in skill
            assert "description" in skill

    def test_list_skills_excludes_specified(self):
        """Should exclude skills in excluded_skills list."""
        from src.skills import list_skills_tool

        result = list_skills_tool(excluded_skills=["speech", "mastodon"])

        skill_names = [s["name"] for s in result["skills"]]
        assert "speech" not in skill_names
        assert "mastodon" not in skill_names
        assert "core" in skill_names

    def test_list_skills_includes_hint(self):
        """Should include usage hint."""
        from src.skills import list_skills_tool

        result = list_skills_tool()

        assert "hint" in result
        assert "skill_usage" in result["hint"]


class TestSkillUsageTool:
    """Test skill_usage meta-tool."""

    def test_skill_usage_returns_help(self):
        """Should return help text for skill."""
        from src.skills import skill_usage_tool

        result = skill_usage_tool("core")

        assert "skill" in result
        assert "usage" in result
        assert result["skill"] == "core"
        assert "topics" in result["usage"].lower()

    def test_skill_usage_error_for_nonexistent(self):
        """Should return error for nonexistent skill."""
        from src.skills import skill_usage_tool

        result = skill_usage_tool("nonexistent_xyz")

        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_skill_usage_handles_invalid_skill(self, tmp_path):
        """Should return error for invalid skill."""
        from src.skills.tools import skill_usage_tool

        # Create mock invalid skill
        with patch('src.skills.discovery.SKILLS_DIR', tmp_path):
            result = skill_usage_tool("nonexistent")

        assert "error" in result


class TestExecuteSkillTool:
    """Test execute_skill meta-tool."""

    def test_execute_skill_runs_command(self):
        """Should execute skill command and return result."""
        from src.skills import execute_skill_tool

        result = execute_skill_tool("core", "dates current")

        assert "success" in result
        assert "output" in result
        assert "exit_code" in result
        assert result["success"] is True
        assert result["exit_code"] == 0

    def test_execute_skill_returns_output(self):
        """Should return command output."""
        from src.skills import execute_skill_tool

        result = execute_skill_tool("core", "dates current")

        assert "Date:" in result["output"]

    def test_execute_skill_handles_failure(self):
        """Should handle command failures."""
        from src.skills import execute_skill_tool

        result = execute_skill_tool("core", "nonexistent_command")

        assert result["success"] is False
        assert result["exit_code"] != 0

    def test_execute_skill_error_for_nonexistent(self):
        """Should return error for nonexistent skill."""
        from src.skills import execute_skill_tool

        result = execute_skill_tool("nonexistent_xyz", "command")

        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_execute_skill_passes_context(self):
        """Should pass agent context to execution."""
        from src.skills.tools import execute_skill_tool
        from src.skills.executor import execute_skill

        with patch('src.skills.tools.execute_skill') as mock_exec:
            mock_exec.return_value = MagicMock(
                success=True,
                output="test",
                exit_code=0
            )

            execute_skill_tool(
                skill="core",
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
        from src.skills import get_meta_tools

        tools = get_meta_tools()

        assert len(tools) == 3

    def test_get_meta_tools_has_correct_names(self):
        """Should have list_skills, skill_usage, execute_skill."""
        from src.skills import get_meta_tools

        tools = get_meta_tools()
        tool_names = [t["name"] for t in tools]

        assert "list_skills" in tool_names
        assert "skill_usage" in tool_names
        assert "execute_skill" in tool_names

    def test_get_meta_tools_has_descriptions(self):
        """Should have descriptions for all tools."""
        from src.skills import get_meta_tools

        tools = get_meta_tools()

        for tool in tools:
            assert "description" in tool
            assert tool["description"]

    def test_get_meta_tools_has_input_schemas(self):
        """Should have input schemas for all tools."""
        from src.skills import get_meta_tools

        tools = get_meta_tools()

        for tool in tools:
            assert "input_schema" in tool
            assert "type" in tool["input_schema"]

    def test_execute_skill_schema_requires_skill_and_command(self):
        """execute_skill should require skill and command params."""
        from src.skills import get_meta_tools

        tools = get_meta_tools()
        exec_tool = next(t for t in tools if t["name"] == "execute_skill")

        schema = exec_tool["input_schema"]
        assert "skill" in schema["required"]
        assert "command" in schema["required"]


class TestExecuteMetaTool:
    """Test the execute_meta_tool dispatcher."""

    def test_execute_meta_tool_list_skills(self):
        """Should dispatch list_skills correctly."""
        from src.skills import execute_meta_tool

        result = execute_meta_tool("list_skills", {})

        assert "skills" in result
        assert "count" in result

    def test_execute_meta_tool_skill_usage(self):
        """Should dispatch skill_usage correctly."""
        from src.skills import execute_meta_tool

        result = execute_meta_tool("skill_usage", {"skill": "core"})

        assert "usage" in result

    def test_execute_meta_tool_execute_skill(self):
        """Should dispatch execute_skill correctly."""
        from src.skills import execute_meta_tool

        result = execute_meta_tool("execute_skill", {
            "skill": "core",
            "command": "dates current"
        })

        assert "success" in result
        assert "output" in result

    def test_execute_meta_tool_unknown_tool(self):
        """Should return error for unknown tool."""
        from src.skills import execute_meta_tool

        result = execute_meta_tool("unknown_tool", {})

        assert "error" in result
        assert "Unknown" in result["error"]

    def test_execute_meta_tool_uses_context(self):
        """Should pass agent context from context dict."""
        from src.skills import execute_meta_tool

        context = {
            "agent_id": "test-agent",
            "excluded_skills": ["speech"]
        }

        result = execute_meta_tool("list_skills", {}, agent_context=context)

        skill_names = [s["name"] for s in result["skills"]]
        assert "speech" not in skill_names
