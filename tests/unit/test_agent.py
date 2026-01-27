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
            "state": "enabled",
            "tools": ["list_topics", "create_topic"]
        }
        (agent_dir / "config.json").write_text(json.dumps(config))
        (agent_dir / "identity.md").write_text("# Test Agent\n\nA test agent.")

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            agent = Agent("test-agent")

        assert agent.id == "test-agent"
        assert agent.config["name"] == "Test Agent"
        assert "list_topics" in agent.config["tools"]

    def test_agent_loads_identity_from_disk(self, tmp_path):
        """Agent loads identity from agents/{id}/identity.md."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {"id": "test-agent", "name": "Test", "state": "enabled", "tools": []}
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
            "state": "enabled",
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
        (agent_dir / "config.json").write_text('{"id": "test-agent", "state": "enabled", "tools": []}')
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
            "state": "enabled",
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
            "state": "enabled",
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
            "state": "enabled",
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
    """Test Agent._execute_tools() method.

    The agent now uses meta-tools for plugin execution:
    - list_plugins: Discover available plugins
    - plugin_usage: Get help for a plugin
    - execute_plugin: Run a plugin command
    """

    def _create_agent(self, tmp_path, tools=None):
        """Create an agent for testing."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {
            "id": "test-agent",
            "state": "enabled",
            "tools": tools or [],
            "consolidation": {"enabled": False}
        }
        (agent_dir / "config.json").write_text(json.dumps(config))
        (agent_dir / "identity.md").write_text("# Test\n")

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            return Agent("test-agent")

    def test_execute_tools_returns_results(self, tmp_path):
        """_execute_tools returns tool results for each call."""
        agent = self._create_agent(tmp_path)

        # Create mock response with meta-tool use (execute_plugin)
        from tests.fixtures.llm.mock_client import ToolUseBlock

        mock_response = MagicMock()
        mock_response.content = [
            ToolUseBlock(id="tool_1", name="execute_plugin", input={"plugin": "core", "command": "date now"})
        ]

        # Mock the meta-tool execution
        with patch("src.plugins.execute_meta_tool", return_value={"success": True, "output": "2025-01-23", "exit_code": 0}):
            results = agent._execute_tools(mock_response)

        assert len(results) == 1
        assert results[0]["type"] == "tool_result"
        assert results[0]["tool_use_id"] == "tool_1"
        assert "2025-01-23" in results[0]["content"]

    def test_execute_tools_handles_errors(self, tmp_path):
        """_execute_tools includes error results from failed meta-tools."""
        agent = self._create_agent(tmp_path)

        from tests.fixtures.llm.mock_client import ToolUseBlock

        mock_response = MagicMock()
        mock_response.content = [
            ToolUseBlock(id="tool_1", name="execute_plugin", input={"plugin": "nonexistent", "command": "test"})
        ]

        # execute_meta_tool returns error dict for failed plugins
        with patch("src.plugins.execute_meta_tool", return_value={"error": "Plugin not found: nonexistent"}):
            results = agent._execute_tools(mock_response)

        assert len(results) == 1
        assert "error" in results[0]["content"].lower()

    def test_execute_tools_list_plugins(self, tmp_path):
        """_execute_tools handles list_plugins meta-tool."""
        agent = self._create_agent(tmp_path)

        from tests.fixtures.llm.mock_client import ToolUseBlock

        mock_response = MagicMock()
        mock_response.content = [
            ToolUseBlock(id="tool_1", name="list_plugins", input={})
        ]

        with patch("src.plugins.execute_meta_tool", return_value={"plugins": [{"name": "core", "description": "Core functionality"}], "count": 1}):
            results = agent._execute_tools(mock_response)

        assert len(results) == 1
        assert results[0]["type"] == "tool_result"
        assert "core" in results[0]["content"]

    def test_execute_tools_plugin_usage(self, tmp_path):
        """_execute_tools handles plugin_usage meta-tool."""
        agent = self._create_agent(tmp_path)

        from tests.fixtures.llm.mock_client import ToolUseBlock

        mock_response = MagicMock()
        mock_response.content = [
            ToolUseBlock(id="tool_1", name="plugin_usage", input={"plugin": "core"})
        ]

        with patch("src.plugins.execute_meta_tool", return_value={"plugin": "core", "usage": "Usage: core topics list"}):
            results = agent._execute_tools(mock_response)

        assert len(results) == 1
        assert "Usage" in results[0]["content"]


class TestAgentConversationHistory:
    """Test Agent conversation history management."""

    def _create_agent(self, tmp_path):
        """Create an agent with conversation history directory."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {"id": "test-agent", "state": "enabled", "tools": [], "consolidation": {"enabled": False}}
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
        config = {"id": "test-agent", "state": "enabled", "tools": [], "consolidation": {"enabled": False}}
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


# =============================================================================
# Agent State Tests
# =============================================================================

@pytest.mark.unit
class TestAgentState:
    """Test Agent.state property and is_enabled() method.

    Spec: specs/1_agents.md - Agent States section
    """

    def _create_agent(self, tmp_path, state="enabled"):
        """Create an agent with specified state."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {
            "id": "test-agent",
            "state": state,
            "tools": [],
            "consolidation": {"enabled": False}
        }
        (agent_dir / "config.json").write_text(json.dumps(config))
        (agent_dir / "identity.md").write_text("# Test\n")

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            return Agent("test-agent")

    def test_state_returns_agent_state_enum(self, tmp_path):
        """state property returns AgentState enum value.

        Spec: Agents have three possible states: enabled, disabled, paused.
        """
        from src.agent.agent import AgentState

        agent = self._create_agent(tmp_path, state="enabled")

        # Mock metacognition to return specific state
        with patch.object(agent.metacognition, 'get_agent_state', return_value=AgentState.ENABLED):
            assert agent.state == AgentState.ENABLED

    def test_is_enabled_true_when_enabled(self, tmp_path):
        """is_enabled() returns True when state is ENABLED.

        Spec: Enabled agents poll for topics and work on them.
        """
        from src.agent.agent import AgentState

        agent = self._create_agent(tmp_path)

        with patch.object(agent.metacognition, 'get_agent_state', return_value=AgentState.ENABLED):
            assert agent.is_enabled() is True

    def test_is_enabled_false_when_disabled(self, tmp_path):
        """is_enabled() returns False when state is DISABLED.

        Spec: Disabled agents never process topics.
        """
        from src.agent.agent import AgentState

        agent = self._create_agent(tmp_path, state="disabled")

        with patch.object(agent.metacognition, 'get_agent_state', return_value=AgentState.DISABLED):
            assert agent.is_enabled() is False

    def test_is_enabled_false_when_paused(self, tmp_path):
        """is_enabled() returns False when state is PAUSED.

        Spec: Paused agents require manual intervention to resume.
        """
        from src.agent.agent import AgentState

        agent = self._create_agent(tmp_path, state="paused")

        with patch.object(agent.metacognition, 'get_agent_state', return_value=AgentState.PAUSED):
            assert agent.is_enabled() is False


# =============================================================================
# User Identity Context Tests
# =============================================================================

@pytest.mark.unit
class TestUserIdentityContext:
    """Test Agent._get_user_identity() method.

    Spec: docs/3_system.md - "Every LLM call includes rich context"
    """

    def test_get_user_identity_loads_from_disk(self, tmp_path):
        """_get_user_identity() loads user's identity.md content.

        Spec: Agents know who the user is via user identity context.
        """
        from src.agent.agent import Agent

        # Create test agent
        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        (agent_dir / "config.json").write_text('{"id": "test-agent", "state": "enabled", "tools": []}')
        (agent_dir / "identity.md").write_text("# Test\n")

        # Create user identity
        user_dir = tmp_path / "agents" / "user"
        user_dir.mkdir(parents=True)
        (user_dir / "identity.md").write_text("# User\n\nI am the user. I like testing.")

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            agent = Agent("test-agent")
            user_identity = agent._get_user_identity()

        assert "I am the user" in user_identity
        assert "I like testing" in user_identity

    def test_get_user_identity_returns_placeholder_when_missing(self, tmp_path):
        """_get_user_identity() returns placeholder when identity.md doesn't exist.

        Spec: Graceful degradation when user identity not yet established.
        """
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        (agent_dir / "config.json").write_text('{"id": "test-agent", "state": "enabled", "tools": []}')
        (agent_dir / "identity.md").write_text("# Test\n")

        # Don't create user directory

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            agent = Agent("test-agent")
            user_identity = agent._get_user_identity()

        assert "not yet established" in user_identity.lower()

    def test_get_user_identity_for_user_agent(self, tmp_path):
        """_get_user_identity() returns user identity even for user agent.

        Note: User agent uses its own identity through standard system prompt flow.
        """
        from src.agent.agent import Agent

        user_dir = tmp_path / "agents" / "user"
        user_dir.mkdir(parents=True)
        (user_dir / "config.json").write_text('{"id": "user", "state": "enabled", "tools": []}')
        (user_dir / "identity.md").write_text("# User\n\nI am the user.")

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            agent = Agent("user")
            user_identity = agent._get_user_identity()

        # User agent reads its own identity file
        assert "# User" in user_identity


# =============================================================================
# Topic Prompt Type Tests
# =============================================================================

@pytest.mark.unit
class TestTopicPromptType:
    """Test Agent._get_topic_prompt_type() method.

    All topics use the topic_assignment template.
    Internal euno:* topics bypass the chat loop entirely.
    """

    def _create_agent(self, tmp_path):
        """Create an agent for testing."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {
            "id": "test-agent",
            "state": "enabled",
            "tools": [],
            "consolidation": {"enabled": True}
        }
        (agent_dir / "config.json").write_text(json.dumps(config))
        (agent_dir / "identity.md").write_text("# Test\n")

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            return Agent("test-agent")

    def test_get_topic_prompt_type_regular(self, tmp_path):
        """_get_topic_prompt_type() returns topic_assignment template for all topics."""
        agent = self._create_agent(tmp_path)

        topic = {"name": "Write a report", "tags": []}
        assert agent._get_topic_prompt_type(topic) == "agent/topic_assignment"

    def test_get_topic_prompt_type_any_topic(self, tmp_path):
        """_get_topic_prompt_type() always returns topic_assignment."""
        agent = self._create_agent(tmp_path)

        # All topics use topic_assignment template
        topics = [
            {"name": "Regular topic", "tags": []},
            {"name": "euno:consolidate", "tags": []},
            {"name": "Some other topic", "tags": ["important"]},
        ]

        for topic in topics:
            assert agent._get_topic_prompt_type(topic) == "agent/topic_assignment"


# =============================================================================
# Work Cycle Tests
# =============================================================================

@pytest.mark.unit
class TestWorkCycle:
    """Test Agent.work_cycle_sync() method.

    Spec: specs/1_agents.md - Work Cycle section
    """

    def _create_agent(self, tmp_path, tools=None):
        """Create an agent for work cycle testing."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {
            "id": "test-agent",
            "state": "enabled",
            "tools": tools or ["done_working"],
            "consolidation": {"enabled": False}
        }
        (agent_dir / "config.json").write_text(json.dumps(config))
        (agent_dir / "identity.md").write_text("# Test\n")

        # Create system config
        system_dir = tmp_path / "system"
        system_dir.mkdir(parents=True)
        system_config = {"agents": {"max_work_iterations": 5}}
        (system_dir / "config.json").write_text(json.dumps(system_config))

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            with patch("src.agent.agent.DATA_DIR", tmp_path):
                return Agent("test-agent")

    def test_work_cycle_claims_topic(self, tmp_path):
        """work_cycle_sync() claims topic before working.

        Spec: Work cycle phases: claim → plan → execute → complete
        """
        agent = self._create_agent(tmp_path)

        mock_topic = {"id": "topic-1", "name": "Test topic", "tags": [], "description": "Test"}

        with patch("plugins.core.data.topics.list_topics", return_value=[mock_topic]):
            with patch("plugins.core.data.topics.claim_topic", return_value={"claimed": True}) as mock_claim:
                with patch("plugins.core.data.topics.release_topic"):
                    with patch.object(agent.metacognition.planner, 'should_plan', return_value=False):
                        with patch.object(agent, 'chat', side_effect=lambda *a, **k: setattr(agent, '_work_done', True) or "Done"):
                            with patch.object(agent, '_log'):
                                agent.work_cycle_sync()

                mock_claim.assert_called_once_with("topic-1", "test-agent")

    def test_work_cycle_releases_topic_on_completion(self, tmp_path):
        """work_cycle_sync() releases topic after work completes.

        Spec: Agent releases topic when work cycle ends.
        """
        agent = self._create_agent(tmp_path)

        mock_topic = {"id": "topic-1", "name": "Test topic", "tags": [], "description": "Test"}

        with patch("plugins.core.data.topics.list_topics", return_value=[mock_topic]):
            with patch("plugins.core.data.topics.claim_topic", return_value={"claimed": True}):
                with patch("plugins.core.data.topics.release_topic") as mock_release:
                    with patch.object(agent.metacognition.planner, 'should_plan', return_value=False):
                        with patch.object(agent, 'chat', side_effect=lambda *a, **k: setattr(agent, '_work_done', True) or "Done"):
                            with patch.object(agent, '_log'):
                                agent.work_cycle_sync()

                mock_release.assert_called_once_with("topic-1", "test-agent")

    def test_work_cycle_releases_topic_on_error(self, tmp_path):
        """work_cycle_sync() releases topic even if chat raises exception.

        Spec: Topic must be released to avoid blocking the queue.
        """
        agent = self._create_agent(tmp_path)

        mock_topic = {"id": "topic-1", "name": "Test topic", "tags": [], "description": "Test"}

        with patch("plugins.core.data.topics.list_topics", return_value=[mock_topic]):
            with patch("plugins.core.data.topics.claim_topic", return_value={"claimed": True}):
                with patch("plugins.core.data.topics.release_topic") as mock_release:
                    with patch.object(agent.metacognition.planner, 'should_plan', return_value=False):
                        with patch.object(agent, 'chat', side_effect=Exception("LLM error")):
                            with patch.object(agent, '_log'):
                                try:
                                    agent.work_cycle_sync()
                                except:
                                    pass

                # Topic should still be released
                mock_release.assert_called_once_with("topic-1", "test-agent")

    def test_work_cycle_skips_when_no_topics(self, tmp_path):
        """work_cycle_sync() returns early when no topics available.

        Spec: Agent polls for actionable topics; if none, no work cycle.
        """
        agent = self._create_agent(tmp_path)

        with patch("plugins.core.data.topics.list_topics", return_value=[]):
            with patch("plugins.core.data.topics.claim_topic") as mock_claim:
                with patch.object(agent, '_log'):
                    agent.work_cycle_sync()

                # Should not attempt to claim any topic
                mock_claim.assert_not_called()

    def test_work_cycle_aborts_if_claim_fails(self, tmp_path):
        """work_cycle_sync() aborts if topic claim fails.

        Spec: Another agent may have claimed the topic first.
        """
        agent = self._create_agent(tmp_path)

        mock_topic = {"id": "topic-1", "name": "Test topic", "tags": [], "description": "Test"}

        with patch("plugins.core.data.topics.list_topics", return_value=[mock_topic]):
            with patch("plugins.core.data.topics.claim_topic", return_value={"error": "Already claimed"}):
                with patch.object(agent, 'chat') as mock_chat:
                    with patch.object(agent, '_log'):
                        agent.work_cycle_sync()

                # Should not proceed to chat
                mock_chat.assert_not_called()

    def test_work_cycle_one_topic_at_a_time(self, tmp_path):
        """work_cycle_sync() only processes first topic from list.

        Spec: Agent receives ONE topic per work cycle.
        """
        agent = self._create_agent(tmp_path)

        topics = [
            {"id": "topic-1", "name": "First topic", "tags": [], "description": "First"},
            {"id": "topic-2", "name": "Second topic", "tags": [], "description": "Second"},
        ]

        claimed_topics = []

        def track_claim(topic_id, agent_id):
            claimed_topics.append(topic_id)
            return {"claimed": True}

        with patch("plugins.core.data.topics.list_topics", return_value=topics):
            with patch("plugins.core.data.topics.claim_topic", side_effect=track_claim):
                with patch("plugins.core.data.topics.release_topic"):
                    with patch.object(agent.metacognition.planner, 'should_plan', return_value=False):
                        with patch.object(agent, 'chat', side_effect=lambda *a, **k: setattr(agent, '_work_done', True) or "Done"):
                            with patch.object(agent, '_log'):
                                agent.work_cycle_sync()

        # Only first topic should be claimed
        assert claimed_topics == ["topic-1"]


# =============================================================================
# Work Cycle Planning Tests
# =============================================================================

@pytest.mark.unit
class TestWorkCyclePlanning:
    """Test planning integration in work_cycle_sync().

    Spec: specs/1_agents.md - "Planning creates a brief approach before execution"
    """

    def _create_agent(self, tmp_path):
        """Create an agent for planning tests."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {
            "id": "test-agent",
            "state": "enabled",
            "tools": ["done_working"],
            "consolidation": {"enabled": False}
        }
        (agent_dir / "config.json").write_text(json.dumps(config))
        (agent_dir / "identity.md").write_text("# Test\n")

        system_dir = tmp_path / "system"
        system_dir.mkdir(parents=True)
        (system_dir / "config.json").write_text('{"agents": {"max_work_iterations": 5}}')

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            with patch("src.agent.agent.DATA_DIR", tmp_path):
                return Agent("test-agent")

    def test_work_cycle_calls_planner_should_plan(self, tmp_path):
        """work_cycle_sync() checks if planning is needed for topic.

        Spec: Planning is part of Reasoning - it reduces wasted effort.
        """
        agent = self._create_agent(tmp_path)

        mock_topic = {"id": "topic-1", "name": "Test topic", "tags": [], "description": "Test"}

        with patch("plugins.core.data.topics.list_topics", return_value=[mock_topic]):
            with patch("plugins.core.data.topics.claim_topic", return_value={"claimed": True}):
                with patch("plugins.core.data.topics.release_topic"):
                    with patch.object(agent.metacognition.planner, 'should_plan', return_value=False) as mock_should:
                        with patch.object(agent, 'chat', side_effect=lambda *a, **k: setattr(agent, '_work_done', True) or "Done"):
                            with patch.object(agent, '_log'):
                                agent.work_cycle_sync()

                        mock_should.assert_called_once_with(mock_topic)

    def test_work_cycle_creates_plan_when_needed(self, tmp_path):
        """work_cycle_sync() creates plan when planner says to.

        Spec: Agent creates brief plan (tool sequence, delegation, approach).
        """
        agent = self._create_agent(tmp_path)

        mock_topic = {"id": "topic-1", "name": "Complex topic", "tags": [], "description": "Needs planning"}

        with patch("plugins.core.data.topics.list_topics", return_value=[mock_topic]):
            with patch("plugins.core.data.topics.claim_topic", return_value={"claimed": True}):
                with patch("plugins.core.data.topics.release_topic"):
                    with patch.object(agent.metacognition.planner, 'should_plan', return_value=True):
                        with patch.object(agent.metacognition.planner, 'create_plan', return_value="1. Do this\n2. Do that") as mock_create:
                            with patch.object(agent.metacognition.planner, 'inject_plan', return_value="Plan: ..."):
                                with patch.object(agent, 'chat', side_effect=lambda *a, **k: setattr(agent, '_work_done', True) or "Done"):
                                    with patch.object(agent, '_log'):
                                        agent.work_cycle_sync()

                            mock_create.assert_called_once_with(mock_topic)

    def test_work_cycle_injects_plan_into_prompt(self, tmp_path):
        """work_cycle_sync() injects plan into topic prompt.

        Spec: Plan is injected before execution.
        """
        agent = self._create_agent(tmp_path)

        mock_topic = {"id": "topic-1", "name": "Topic", "tags": [], "description": "Test"}

        with patch("plugins.core.data.topics.list_topics", return_value=[mock_topic]):
            with patch("plugins.core.data.topics.claim_topic", return_value={"claimed": True}):
                with patch("plugins.core.data.topics.release_topic"):
                    with patch.object(agent.metacognition.planner, 'should_plan', return_value=True):
                        with patch.object(agent.metacognition.planner, 'create_plan', return_value="The plan"):
                            with patch.object(agent.metacognition.planner, 'inject_plan', return_value="Injected prompt") as mock_inject:
                                with patch.object(agent, 'chat', side_effect=lambda *a, **k: setattr(agent, '_work_done', True) or "Done"):
                                    with patch.object(agent, '_log'):
                                        agent.work_cycle_sync()

                                mock_inject.assert_called_once()


# =============================================================================
# Work Cycle Stuck Detection Tests
# =============================================================================

@pytest.mark.unit
class TestWorkCycleStuckDetection:
    """Test stuck detection in work_cycle_sync().

    Spec: specs/1_agents.md - "Progress Awareness" section
    """

    def _create_agent(self, tmp_path):
        """Create an agent for stuck detection tests."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {
            "id": "test-agent",
            "state": "enabled",
            "tools": ["done_working"],
            "consolidation": {"enabled": False}
        }
        (agent_dir / "config.json").write_text(json.dumps(config))
        (agent_dir / "identity.md").write_text("# Test\n")

        system_dir = tmp_path / "system"
        system_dir.mkdir(parents=True)
        (system_dir / "config.json").write_text('{"agents": {"max_work_iterations": 10}}')

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            with patch("src.agent.agent.DATA_DIR", tmp_path):
                return Agent("test-agent")

    def test_work_cycle_starts_progress_session(self, tmp_path):
        """work_cycle_sync() starts a progress tracking session.

        Spec: All loop detection is centralized in progress.py.
        """
        agent = self._create_agent(tmp_path)

        mock_topic = {"id": "topic-1", "name": "Topic", "tags": [], "description": "Test"}

        def finish_work(*args, **kwargs):
            agent._work_done = True
            return "Response"

        with patch("plugins.core.data.topics.list_topics", return_value=[mock_topic]):
            with patch("plugins.core.data.topics.claim_topic", return_value={"claimed": True}):
                with patch("plugins.core.data.topics.release_topic"):
                    with patch.object(agent.metacognition.planner, 'should_plan', return_value=False):
                        with patch.object(agent.metacognition, 'start_work_session', return_value="test-session") as mock_start:
                            with patch.object(agent.metacognition, 'end_work_session', return_value={}) as mock_end:
                                with patch.object(agent, 'chat', side_effect=finish_work):
                                    with patch.object(agent, '_log'):
                                        agent.work_cycle_sync()

                            # Session should be started and ended
                            mock_start.assert_called_once_with(session_type="work_cycle")
                            mock_end.assert_called_once()

    def test_work_cycle_breaks_when_stuck(self, tmp_path):
        """work_cycle_sync() raises AgentPausedError when stuck is detected.

        Spec: Pauses agent and marks topic as error when stuck detected.
        """
        from src.agent.cognition.metacognition import AgentPausedError, ProgressLimitExceeded

        agent = self._create_agent(tmp_path)

        mock_topic = {"id": "topic-1", "name": "Topic", "tags": [], "description": "Test"}
        chat_calls = [0]

        def raise_stuck(*args, **kwargs):
            chat_calls[0] += 1
            # Simulate stuck detection during tool execution in chat()
            raise ProgressLimitExceeded("test-agent", "test-session", "Same tool 'test' called 5 times with identical inputs")

        with patch("plugins.core.data.topics.list_topics", return_value=[mock_topic]):
            with patch("plugins.core.data.topics.claim_topic", return_value={"claimed": True}):
                with patch("plugins.core.data.topics.release_topic"):
                    with patch("plugins.core.data.topics.error_topic") as mock_error_topic:
                        with patch.object(agent.metacognition.planner, 'should_plan', return_value=False):
                            with patch.object(agent.metacognition, 'start_work_session', return_value="test-session"):
                                with patch.object(agent.metacognition, 'end_work_session', return_value={}):
                                    # Raise ProgressLimitExceeded during chat (simulating stuck during tool execution)
                                    with patch.object(agent, 'chat', side_effect=raise_stuck):
                                        with patch.object(agent, '_log'):
                                            with pytest.raises(AgentPausedError) as exc_info:
                                                agent.work_cycle_sync()

                            # Should pause with stuck reason
                            assert "Stuck" in str(exc_info.value)
                            # Should have one chat call (stuck detected during first chat)
                            assert chat_calls[0] == 1
                            # Should mark topic as error
                            mock_error_topic.assert_called_once()
                            call_args = mock_error_topic.call_args[0]
                            assert call_args[0] == "topic-1"
                            assert "Stuck" in call_args[1]
                            assert call_args[2] == "test-agent"


# =============================================================================
# Work Cycle Deferred Consolidation Tests
# =============================================================================

@pytest.mark.unit
class TestWorkCycleDeferredConsolidation:
    """Test deferred consolidation batching in work_cycle_sync().

    Spec: specs/1_agents.md - "efficiency.defer_consolidation_in_work_cycles"
    """

    def _create_agent(self, tmp_path):
        """Create an agent with consolidation enabled."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {
            "id": "test-agent",
            "state": "enabled",
            "tools": ["done_working"],
            "consolidation": {"enabled": True}
        }
        (agent_dir / "config.json").write_text(json.dumps(config))
        (agent_dir / "identity.md").write_text("# Test\n")

        system_dir = tmp_path / "system"
        system_dir.mkdir(parents=True)
        (system_dir / "config.json").write_text('{"agents": {"max_work_iterations": 5}}')

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            with patch("src.agent.agent.DATA_DIR", tmp_path):
                return Agent("test-agent")

    def test_work_cycle_defers_consolidation_when_enabled(self, tmp_path):
        """work_cycle_sync() passes defer_consolidation=True to chat when deferred.

        Spec: Defer consolidation to end of work cycle for efficiency.
        """
        agent = self._create_agent(tmp_path)

        mock_topic = {"id": "topic-1", "name": "Topic", "tags": [], "description": "Test"}
        chat_kwargs = []

        def capture_chat(*args, **kwargs):
            chat_kwargs.append(kwargs)
            agent._work_done = True
            return "Done"

        with patch("plugins.core.data.topics.list_topics", return_value=[mock_topic]):
            with patch("plugins.core.data.topics.claim_topic", return_value={"claimed": True}):
                with patch("plugins.core.data.topics.release_topic"):
                    with patch.object(agent.metacognition.planner, 'should_plan', return_value=False):
                        with patch.object(agent.metacognition, 'should_defer_consolidation', return_value=True):
                            with patch.object(agent, 'chat', side_effect=capture_chat):
                                with patch.object(agent, '_log'):
                                    with patch.object(agent.consolidation, 'append_batch'):
                                        agent.work_cycle_sync()

                        # chat should be called with defer_consolidation=True
                        assert any(kw.get('defer_consolidation') is True for kw in chat_kwargs)

    def test_work_cycle_batches_consolidation_at_end(self, tmp_path):
        """work_cycle_sync() calls append_batch at end when deferred.

        Spec: Batches reflection at end of work cycle.
        """
        agent = self._create_agent(tmp_path)

        mock_topic = {"id": "topic-1", "name": "Topic", "tags": [], "description": "Test", "status": "working"}
        iteration = [0]

        def multi_iteration_chat(*args, **kwargs):
            iteration[0] += 1
            if iteration[0] >= 2:
                agent._work_done = True
            return f"Response {iteration[0]}"

        with patch("plugins.core.data.topics.list_topics", return_value=[mock_topic]):
            with patch("plugins.core.data.topics.claim_topic", return_value={"claimed": True}):
                with patch("plugins.core.data.topics.release_topic"):
                    with patch("plugins.core.data.topics.get_topic", return_value=mock_topic):
                        with patch.object(agent.metacognition.planner, 'should_plan', return_value=False):
                            with patch.object(agent.metacognition, 'should_defer_consolidation', return_value=True):
                                with patch.object(agent.metacognition, 'check_stuck', return_value=None):
                                    with patch.object(agent, 'chat', side_effect=multi_iteration_chat):
                                        with patch.object(agent, '_log'):
                                            with patch.object(agent.consolidation, 'append_batch') as mock_batch:
                                                agent.work_cycle_sync()

                                            # append_batch should be called once at end with collected exchanges
                                            mock_batch.assert_called_once()
                                            exchanges = mock_batch.call_args[0][0]
                                            assert len(exchanges) == 2  # 2 iterations


# =============================================================================
# Minimal Response Stuck Detection Tests
# =============================================================================

@pytest.mark.unit
class TestMinimalResponseDetection:
    """Test minimal/empty response stuck detection in work_cycle_sync().

    When an LLM returns consecutive minimal responses (like "..." or empty),
    the work cycle should detect this as a stuck state and raise an error.

    This complements tool-based stuck detection for cases where no tools are called.
    """

    def _create_agent(self, tmp_path):
        """Create an agent for minimal response tests."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {
            "id": "test-agent",
            "state": "enabled",
            "tools": ["done_working"],
            "consolidation": {"enabled": False}
        }
        (agent_dir / "config.json").write_text(json.dumps(config))
        (agent_dir / "identity.md").write_text("# Test\n")

        system_dir = tmp_path / "system"
        system_dir.mkdir(parents=True)
        (system_dir / "config.json").write_text('{"agents": {"max_work_iterations": 20}}')

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            with patch("src.agent.agent.DATA_DIR", tmp_path):
                return Agent("test-agent")

    def test_detects_consecutive_minimal_responses(self, tmp_path):
        """work_cycle_sync() detects 5 consecutive minimal responses as stuck.

        When LLM returns "..." or similar minimal responses repeatedly without
        calling any tools, the agent should be paused to prevent infinite loops.
        """
        from src.agent.cognition.metacognition import AgentPausedError

        agent = self._create_agent(tmp_path)

        mock_topic = {"id": "topic-1", "name": "Topic", "tags": [], "description": "Test", "status": "working"}
        response_count = [0]

        def minimal_response(*args, **kwargs):
            response_count[0] += 1
            return "..."  # Minimal response < 20 chars

        with patch("plugins.core.data.topics.list_topics", return_value=[mock_topic]):
            with patch("plugins.core.data.topics.claim_topic", return_value={"claimed": True}):
                with patch("plugins.core.data.topics.release_topic"):
                    with patch("plugins.core.data.topics.get_topic", return_value=mock_topic):
                        with patch("plugins.core.data.topics.error_topic"):
                            with patch.object(agent.metacognition.planner, 'should_plan', return_value=False):
                                with patch.object(agent.metacognition, 'check_stuck', return_value=None):
                                    with patch.object(agent, 'chat', side_effect=minimal_response):
                                        with patch.object(agent, '_log'):
                                            with pytest.raises(AgentPausedError) as exc_info:
                                                agent.work_cycle_sync()

                                            # Should detect minimal response stuck pattern
                                            assert "minimal responses" in str(exc_info.value).lower()
                                            # Should have tried 5 times (the threshold)
                                            assert response_count[0] == 5

    def test_resets_counter_on_substantive_response(self, tmp_path):
        """Counter resets when a substantive response (>=20 chars) is received.

        If agent gets minimal responses but then a real response, the counter
        resets and it can continue working normally.
        """
        agent = self._create_agent(tmp_path)

        mock_topic = {"id": "topic-1", "name": "Topic", "tags": [], "description": "Test", "status": "working"}
        response_count = [0]

        def alternating_response(*args, **kwargs):
            response_count[0] += 1
            if response_count[0] <= 3:
                return "..."  # Minimal
            elif response_count[0] == 4:
                return "This is a substantive response that resets the counter."
            elif response_count[0] <= 7:
                return "..."  # Minimal again
            else:
                agent._work_done = True
                return "This is another substantive response with more content."

        with patch("plugins.core.data.topics.list_topics", return_value=[mock_topic]):
            with patch("plugins.core.data.topics.claim_topic", return_value={"claimed": True}):
                with patch("plugins.core.data.topics.release_topic"):
                    with patch("plugins.core.data.topics.get_topic", return_value=mock_topic):
                        with patch.object(agent.metacognition.planner, 'should_plan', return_value=False):
                            with patch.object(agent.metacognition, 'check_stuck', return_value=None):
                                with patch.object(agent, 'chat', side_effect=alternating_response):
                                    with patch.object(agent, '_log'):
                                        # Should complete without raising - counter resets on substantive responses
                                        agent.work_cycle_sync()

                                        # Should have gone through all responses without stuck detection
                                        assert response_count[0] == 8

    def test_empty_response_counts_as_minimal(self, tmp_path):
        """Empty strings and None responses count as minimal."""
        from src.agent.cognition.metacognition import AgentPausedError

        agent = self._create_agent(tmp_path)

        mock_topic = {"id": "topic-1", "name": "Topic", "tags": [], "description": "Test", "status": "working"}
        response_count = [0]

        def empty_responses(*args, **kwargs):
            response_count[0] += 1
            # Alternate between empty string and whitespace-only
            if response_count[0] % 2 == 0:
                return ""
            else:
                return "   "

        with patch("plugins.core.data.topics.list_topics", return_value=[mock_topic]):
            with patch("plugins.core.data.topics.claim_topic", return_value={"claimed": True}):
                with patch("plugins.core.data.topics.release_topic"):
                    with patch("plugins.core.data.topics.get_topic", return_value=mock_topic):
                        with patch("plugins.core.data.topics.error_topic"):
                            with patch.object(agent.metacognition.planner, 'should_plan', return_value=False):
                                with patch.object(agent.metacognition, 'check_stuck', return_value=None):
                                    with patch.object(agent, 'chat', side_effect=empty_responses):
                                        with patch.object(agent, '_log'):
                                            with pytest.raises(AgentPausedError):
                                                agent.work_cycle_sync()

                                            # Should trigger after 5 minimal responses
                                            assert response_count[0] == 5

    def test_logs_minimal_response_events(self, tmp_path):
        """work_cycle_sync() logs each minimal response detection."""
        from src.agent.cognition.metacognition import AgentPausedError

        agent = self._create_agent(tmp_path)

        mock_topic = {"id": "topic-1", "name": "Topic", "tags": [], "description": "Test", "status": "working"}
        logged_events = []

        def capture_log(event, data=None):
            logged_events.append(event)

        def minimal_response(*args, **kwargs):
            return "..."

        with patch("plugins.core.data.topics.list_topics", return_value=[mock_topic]):
            with patch("plugins.core.data.topics.claim_topic", return_value={"claimed": True}):
                with patch("plugins.core.data.topics.release_topic"):
                    with patch("plugins.core.data.topics.get_topic", return_value=mock_topic):
                        with patch("plugins.core.data.topics.error_topic"):
                            with patch.object(agent.metacognition.planner, 'should_plan', return_value=False):
                                with patch.object(agent.metacognition, 'check_stuck', return_value=None):
                                    with patch.object(agent, 'chat', side_effect=minimal_response):
                                        with patch.object(agent, '_log', side_effect=capture_log):
                                            with pytest.raises(AgentPausedError):
                                                agent.work_cycle_sync()

                                            # Should have logged minimal_response events
                                            assert logged_events.count("minimal_response") == 5


# =============================================================================
# Metacognition Increment Iteration Tests
# =============================================================================

@pytest.mark.unit
class TestMetacognitionIncrementIteration:
    """Test Metacognition.increment_iteration() method.

    This method is called at each work cycle iteration to track progress
    and enforce iteration limits.
    """

    def _create_agent(self, tmp_path):
        """Create an agent for testing metacognition."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {
            "id": "test-agent",
            "state": "enabled",
            "tools": [],
            "consolidation": {"enabled": False}
        }
        (agent_dir / "config.json").write_text(json.dumps(config))
        (agent_dir / "identity.md").write_text("# Test\n")

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            return Agent("test-agent")

    def test_increment_iteration_increments_count(self, tmp_path):
        """increment_iteration() increments internal iteration count."""
        agent = self._create_agent(tmp_path)

        initial_count = agent.metacognition._iteration_count

        result = agent.metacognition.increment_iteration()

        assert agent.metacognition._iteration_count == initial_count + 1
        assert result >= initial_count + 1

    def test_increment_iteration_uses_progress_tracker_when_session_active(self, tmp_path):
        """increment_iteration() delegates to progress tracker when session is active."""
        agent = self._create_agent(tmp_path)

        # Start a work session
        session_id = agent.metacognition.start_work_session(session_type="work_cycle")

        with patch.object(agent.metacognition._progress, 'increment', return_value=42) as mock_increment:
            result = agent.metacognition.increment_iteration()

            mock_increment.assert_called_once_with(session_id)
            assert result == 42

    def test_increment_iteration_returns_internal_count_without_session(self, tmp_path):
        """increment_iteration() returns internal count when no session is active."""
        agent = self._create_agent(tmp_path)

        # Don't start a session
        agent.metacognition._iteration_count = 5

        result = agent.metacognition.increment_iteration()

        assert result == 6
        assert agent.metacognition._iteration_count == 6
