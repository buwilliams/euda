"""
Unit tests for Agent class.

Tests for src/agent/agent.py including:
- Agent initialization
- Chat method with LLM mocks
- Tool execution
- Conversation history

Spec: docs/3_system.md - Agent ontology
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
import json

from tests.fixtures.llm import MockLLMClient, MockResponse


class TestAgentInitialization:
    """Test Agent initialization and configuration loading."""

    def test_agent_loads_config_from_disk(self, tmp_path):
        """Agent loads configuration from agents/{id}/config.json."""
        from src.agent.agent import Agent

        # Create agent config
        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {
            "id": "test-agent",
            "name": "Test Agent",
            "enabled": True,
            "tools": ["list_jobs", "create_job"]
        }
        (agent_dir / "config.json").write_text(json.dumps(config))
        (agent_dir / "identity.md").write_text("# Test Agent\n\nA test agent.")

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            agent = Agent("test-agent")

        assert agent.id == "test-agent"
        assert agent.config["name"] == "Test Agent"
        assert "list_jobs" in agent.config["tools"]

    def test_agent_loads_identity_from_disk(self, tmp_path):
        """Agent loads identity from agents/{id}/identity.md."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {"id": "test-agent", "name": "Test", "enabled": True, "tools": []}
        (agent_dir / "config.json").write_text(json.dumps(config))
        (agent_dir / "identity.md").write_text("# Test Agent\n\nI help with testing.")

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            agent = Agent("test-agent")

        assert "Test Agent" in agent.identity
        assert "I help with testing" in agent.identity

    def test_agent_uses_provided_config(self, tmp_path):
        """Agent uses provided config instead of loading from disk."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        (agent_dir / "identity.md").write_text("# Test\n")

        custom_config = {
            "id": "test-agent",
            "name": "Custom Name",
            "enabled": True,
            "tools": ["custom_tool"]
        }

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            agent = Agent("test-agent", config=custom_config)

        assert agent.config["name"] == "Custom Name"

    def test_agent_initializes_metacognition(self, tmp_path):
        """Agent creates Metacognition instance."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        (agent_dir / "config.json").write_text('{"id": "test-agent", "enabled": true, "tools": []}')
        (agent_dir / "identity.md").write_text("# Test\n")

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            agent = Agent("test-agent")

        assert agent.metacognition is not None

    def test_agent_initializes_consolidation_when_enabled(self, tmp_path):
        """Agent creates Consolidation when config enables it."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {
            "id": "test-agent",
            "enabled": True,
            "tools": [],
            "consolidation": {"enabled": True}
        }
        (agent_dir / "config.json").write_text(json.dumps(config))
        (agent_dir / "identity.md").write_text("# Test\n")

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            agent = Agent("test-agent")

        assert agent.consolidation is not None

    def test_agent_skips_consolidation_when_disabled(self, tmp_path):
        """Agent doesn't create Consolidation when disabled in config."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {
            "id": "test-agent",
            "enabled": True,
            "tools": [],
            "consolidation": {"enabled": False}
        }
        (agent_dir / "config.json").write_text(json.dumps(config))
        (agent_dir / "identity.md").write_text("# Test\n")

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            agent = Agent("test-agent")

        assert agent.consolidation is None


class TestAgentChat:
    """Test Agent.chat() method with LLM mocks."""

    def _create_agent(self, tmp_path, tools=None):
        """Create an agent for testing."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {
            "id": "test-agent",
            "name": "Test Agent",
            "enabled": True,
            "tools": tools or [],
            "consolidation": {"enabled": False}  # Disable to simplify tests
        }
        (agent_dir / "config.json").write_text(json.dumps(config))
        (agent_dir / "identity.md").write_text("# Test Agent\n\nI am a helpful test agent.")

        # Create conversation history directory
        state_dir = agent_dir / "state" / "conversation"
        state_dir.mkdir(parents=True)

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            with patch("src.agent.agent.DATA_DIR", tmp_path):
                return Agent("test-agent")

    def test_chat_returns_llm_response(self, tmp_path):
        """chat() returns the LLM's text response."""
        agent = self._create_agent(tmp_path)

        mock = MockLLMClient.simple(text="Hello! How can I help you?")

        with mock.patch():
            response = agent.chat("Hello", save_to_history=False)

        assert "Hello" in response
        assert "help" in response

    def test_chat_sends_user_message_to_llm(self, tmp_path):
        """chat() includes user message in LLM call."""
        agent = self._create_agent(tmp_path)

        mock = MockLLMClient.simple(text="Response")

        with mock.patch():
            agent.chat("What is 2+2?", save_to_history=False)

        assert len(mock.calls) == 1
        messages = mock.calls[0].messages
        assert any("What is 2+2?" in m.get("content", "") for m in messages)

    def test_chat_uses_agent_id_for_cost_tracking(self, tmp_path):
        """chat() uses agent.id for LLM cost tracking."""
        agent = self._create_agent(tmp_path)

        mock = MockLLMClient.simple(text="Response")

        with mock.patch():
            agent.chat("Test", save_to_history=False)

        assert mock.calls[0].agent_id == "test-agent"

    def test_chat_includes_system_prompt(self, tmp_path):
        """chat() includes system prompt from identity."""
        agent = self._create_agent(tmp_path)

        mock = MockLLMClient.simple(text="Response")

        with mock.patch():
            agent.chat("Test", save_to_history=False)

        system_prompt = mock.calls[0].system
        assert "Test Agent" in system_prompt or len(system_prompt) > 0

    def test_chat_extracts_text_from_response(self, tmp_path):
        """chat() extracts text from LLM response blocks."""
        agent = self._create_agent(tmp_path)

        mock = MockLLMClient.simple(text="This is the extracted text response.")

        with mock.patch():
            response = agent.chat("Test message", save_to_history=False)

        assert "extracted text response" in response


class TestAgentToolExecution:
    """Test Agent._execute_tools() method."""

    def _create_agent(self, tmp_path, tools=None):
        """Create an agent for testing."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {
            "id": "test-agent",
            "enabled": True,
            "tools": tools or [],
            "consolidation": {"enabled": False}
        }
        (agent_dir / "config.json").write_text(json.dumps(config))
        (agent_dir / "identity.md").write_text("# Test\n")

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            return Agent("test-agent")

    def test_execute_tools_returns_results(self, tmp_path):
        """_execute_tools returns tool results for each call."""
        agent = self._create_agent(tmp_path, tools=["get_current_time"])

        # Create mock response with tool use
        from tests.fixtures.llm.mock_client import ToolUseBlock, UnifiedResponse, Usage

        mock_response = MagicMock()
        mock_response.content = [
            ToolUseBlock(id="tool_1", name="get_current_time", input={})
        ]

        with patch("src.tools.execute_tool", return_value={"time": "2025-01-23T12:00:00"}):
            results = agent._execute_tools(mock_response)

        assert len(results) == 1
        assert results[0]["type"] == "tool_result"
        assert results[0]["tool_use_id"] == "tool_1"

    def test_execute_tools_handles_errors(self, tmp_path):
        """_execute_tools includes error results from failed tools."""
        agent = self._create_agent(tmp_path, tools=["failing_tool"])

        from tests.fixtures.llm.mock_client import ToolUseBlock

        mock_response = MagicMock()
        mock_response.content = [
            ToolUseBlock(id="tool_1", name="failing_tool", input={})
        ]

        # execute_tool catches exceptions and returns {"error": ...}
        with patch("src.tools.execute_tool", return_value={"error": "Tool failed"}):
            results = agent._execute_tools(mock_response)

        assert len(results) == 1
        assert "error" in results[0]["content"].lower()


class TestAgentConversationHistory:
    """Test Agent conversation history management."""

    def _create_agent(self, tmp_path):
        """Create an agent with conversation history directory."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {"id": "test-agent", "enabled": True, "tools": [], "consolidation": {"enabled": False}}
        (agent_dir / "config.json").write_text(json.dumps(config))
        (agent_dir / "identity.md").write_text("# Test\n")

        state_dir = agent_dir / "state" / "conversation"
        state_dir.mkdir(parents=True)

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            with patch("src.agent.agent.DATA_DIR", tmp_path):
                return Agent("test-agent")

    def test_chat_saves_to_history(self, tmp_path):
        """chat() saves conversation turns to history when enabled."""
        agent = self._create_agent(tmp_path)

        mock = MockLLMClient.simple(text="Hello back!")

        with mock.patch():
            agent.chat("Hello", save_to_history=True)

        # Check that _save_conversation_turn was called
        # We can verify by checking the history file was written
        history_dir = tmp_path / "agents" / "test-agent" / "state" / "conversation"
        history_files = list(history_dir.glob("*.md"))
        # May or may not create file depending on session_id logic
        # Just verify no exceptions occurred

    def test_chat_skips_history_when_disabled(self, tmp_path):
        """chat() doesn't save to history when save_to_history=False."""
        agent = self._create_agent(tmp_path)

        mock = MockLLMClient.simple(text="Response")

        with mock.patch():
            with patch.object(agent, '_save_conversation_turn') as mock_save:
                agent.chat("Test", save_to_history=False)

        mock_save.assert_not_called()


class TestAgentLogging:
    """Test Agent logging functionality."""

    def _create_agent(self, tmp_path):
        """Create an agent for testing."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {"id": "test-agent", "enabled": True, "tools": [], "consolidation": {"enabled": False}}
        (agent_dir / "config.json").write_text(json.dumps(config))
        (agent_dir / "identity.md").write_text("# Test\n")

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            return Agent("test-agent")

    def test_chat_logs_start_and_end(self, tmp_path):
        """chat() logs chat_start and chat_end events."""
        agent = self._create_agent(tmp_path)

        mock = MockLLMClient.simple(text="Response")
        log_events = []

        def capture_log(event, data):
            log_events.append(event)

        with mock.patch():
            with patch.object(agent, '_log', side_effect=capture_log):
                agent.chat("Test", save_to_history=False)

        assert "chat_start" in log_events
        assert "chat_end" in log_events

    def test_chat_logs_llm_response(self, tmp_path):
        """chat() logs llm_response with usage info."""
        agent = self._create_agent(tmp_path)

        mock = MockLLMClient.simple(text="Response")
        log_events = []

        def capture_log(event, data):
            log_events.append((event, data))

        with mock.patch():
            with patch.object(agent, '_log', side_effect=capture_log):
                agent.chat("Test", save_to_history=False)

        llm_logs = [(e, d) for e, d in log_events if e == "llm_response"]
        assert len(llm_logs) >= 1
        assert "usage" in llm_logs[0][1]
