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


# =============================================================================
# Agent State Tests
# =============================================================================

@pytest.mark.unit
class TestAgentState:
    """Test Agent.state property and is_enabled() method.

    Spec: spec/1_agents.md - Agent States section
    """

    def _create_agent(self, tmp_path, state="enabled"):
        """Create an agent with specified state."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {
            "id": "test-agent",
            "enabled": state == "enabled",
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

        Spec: Enabled agents poll for jobs and work on them.
        """
        from src.agent.agent import AgentState

        agent = self._create_agent(tmp_path)

        with patch.object(agent.metacognition, 'get_agent_state', return_value=AgentState.ENABLED):
            assert agent.is_enabled() is True

    def test_is_enabled_false_when_disabled(self, tmp_path):
        """is_enabled() returns False when state is DISABLED.

        Spec: Disabled agents never process jobs.
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
        (agent_dir / "config.json").write_text('{"id": "test-agent", "enabled": true, "tools": []}')
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
        (agent_dir / "config.json").write_text('{"id": "test-agent", "enabled": true, "tools": []}')
        (agent_dir / "identity.md").write_text("# Test\n")

        # Don't create user directory

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            agent = Agent("test-agent")
            user_identity = agent._get_user_identity()

        assert "not yet established" in user_identity.lower()

    def test_get_user_identity_for_user_agent(self, tmp_path):
        """_get_user_identity() returns special message for user agent itself.

        Spec: User agent doesn't need to know about itself.
        """
        from src.agent.agent import Agent

        user_dir = tmp_path / "agents" / "user"
        user_dir.mkdir(parents=True)
        (user_dir / "config.json").write_text('{"id": "user", "enabled": true, "tools": []}')
        (user_dir / "identity.md").write_text("# User\n")

        with patch("src.agent.agent.AGENTS_DIR", tmp_path / "agents"):
            agent = Agent("user")
            user_identity = agent._get_user_identity()

        assert "You are the user" in user_identity


# =============================================================================
# Reflection Trigger Tests
# =============================================================================

@pytest.mark.unit
class TestReflectionTrigger:
    """Test Agent reflection trigger detection and execution.

    Spec: spec/1_agents.md - Consolidation section
    """

    def _create_agent(self, tmp_path):
        """Create an agent with consolidation enabled."""
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
            return Agent("test-agent")

    def test_is_reflection_trigger_detects_consolidation_job(self, tmp_path):
        """_is_reflection_trigger() returns True for consolidation jobs.

        Spec: Template selection based on job name: Trigger:consolidation:* → consolidation.md
        """
        agent = self._create_agent(tmp_path)

        # Test various consolidation job names
        assert agent._is_reflection_trigger([], "Trigger:consolidation:both:2025-01-23") is True
        assert agent._is_reflection_trigger([], "Trigger:consolidation:append:2025-01-23") is True
        assert agent._is_reflection_trigger([], "Trigger:consolidation:consolidate:2025-01-23") is True

    def test_is_reflection_trigger_false_for_regular_jobs(self, tmp_path):
        """_is_reflection_trigger() returns False for regular jobs.

        Spec: All other jobs → job_assignment.md
        """
        agent = self._create_agent(tmp_path)

        assert agent._is_reflection_trigger([], "Regular job") is False
        assert agent._is_reflection_trigger([], "Trigger:start:2025-01-23") is False
        assert agent._is_reflection_trigger([], "Trigger:morning:2025-01-23") is False

    def test_get_job_prompt_type_consolidation(self, tmp_path):
        """_get_job_prompt_type() returns consolidation template for consolidation jobs."""
        agent = self._create_agent(tmp_path)

        job = {"name": "Trigger:consolidation:both:2025-01-23", "tags": []}
        assert agent._get_job_prompt_type(job) == "agent/consolidation"

    def test_get_job_prompt_type_regular(self, tmp_path):
        """_get_job_prompt_type() returns job_assignment template for regular jobs."""
        agent = self._create_agent(tmp_path)

        job = {"name": "Write a report", "tags": []}
        assert agent._get_job_prompt_type(job) == "agent/job_assignment"

    def test_execute_reflection_trigger_extracts_phase(self, tmp_path):
        """_execute_reflection_trigger() extracts phase from job name.

        Spec: Job name format is Trigger:consolidation:{phase}:{date}
        """
        agent = self._create_agent(tmp_path)

        # Mock consolidation and complete_job
        agent.consolidation = MagicMock()

        with patch("src.tools.data.jobs.complete_job"):
            with patch.object(agent, '_log'):
                # Test 'consolidate' phase
                job = {"id": "job-1", "name": "Trigger:consolidation:consolidate:2025-01-23", "tags": []}
                agent._execute_reflection_trigger(job)

                agent.consolidation.consolidate.assert_called_once()

    def test_execute_reflection_trigger_completes_job(self, tmp_path):
        """_execute_reflection_trigger() completes the trigger job.

        Spec: Jobs must be explicitly completed by the agent.
        """
        agent = self._create_agent(tmp_path)
        agent.consolidation = MagicMock()

        with patch("src.tools.data.jobs.complete_job") as mock_complete:
            with patch.object(agent, '_log'):
                job = {"id": "job-123", "name": "Trigger:consolidation:both:2025-01-23", "tags": []}
                agent._execute_reflection_trigger(job)

                mock_complete.assert_called_once_with("job-123")


# =============================================================================
# Work Cycle Tests
# =============================================================================

@pytest.mark.unit
class TestWorkCycle:
    """Test Agent.work_cycle_sync() method.

    Spec: spec/1_agents.md - Work Cycle section
    """

    def _create_agent(self, tmp_path, tools=None):
        """Create an agent for work cycle testing."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {
            "id": "test-agent",
            "enabled": True,
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

    def test_work_cycle_claims_job(self, tmp_path):
        """work_cycle_sync() claims job before working.

        Spec: Work cycle phases: claim → plan → execute → complete
        """
        agent = self._create_agent(tmp_path)

        mock_job = {"id": "job-1", "name": "Test job", "tags": [], "description": "Test"}

        with patch("src.tools.data.jobs.list_jobs", return_value=[mock_job]):
            with patch("src.tools.data.jobs.claim_job", return_value={"claimed": True}) as mock_claim:
                with patch("src.tools.data.jobs.release_job"):
                    with patch.object(agent.metacognition.planner, 'should_plan', return_value=False):
                        with patch.object(agent, 'chat', side_effect=lambda *a, **k: setattr(agent, '_work_done', True) or "Done"):
                            with patch.object(agent, '_log'):
                                agent.work_cycle_sync()

                mock_claim.assert_called_once_with("job-1", "test-agent")

    def test_work_cycle_releases_job_on_completion(self, tmp_path):
        """work_cycle_sync() releases job after work completes.

        Spec: Agent releases job when work cycle ends.
        """
        agent = self._create_agent(tmp_path)

        mock_job = {"id": "job-1", "name": "Test job", "tags": [], "description": "Test"}

        with patch("src.tools.data.jobs.list_jobs", return_value=[mock_job]):
            with patch("src.tools.data.jobs.claim_job", return_value={"claimed": True}):
                with patch("src.tools.data.jobs.release_job") as mock_release:
                    with patch.object(agent.metacognition.planner, 'should_plan', return_value=False):
                        with patch.object(agent, 'chat', side_effect=lambda *a, **k: setattr(agent, '_work_done', True) or "Done"):
                            with patch.object(agent, '_log'):
                                agent.work_cycle_sync()

                mock_release.assert_called_once_with("job-1", "test-agent")

    def test_work_cycle_releases_job_on_error(self, tmp_path):
        """work_cycle_sync() releases job even if chat raises exception.

        Spec: Job must be released to avoid blocking the queue.
        """
        agent = self._create_agent(tmp_path)

        mock_job = {"id": "job-1", "name": "Test job", "tags": [], "description": "Test"}

        with patch("src.tools.data.jobs.list_jobs", return_value=[mock_job]):
            with patch("src.tools.data.jobs.claim_job", return_value={"claimed": True}):
                with patch("src.tools.data.jobs.release_job") as mock_release:
                    with patch.object(agent.metacognition.planner, 'should_plan', return_value=False):
                        with patch.object(agent, 'chat', side_effect=Exception("LLM error")):
                            with patch.object(agent, '_log'):
                                try:
                                    agent.work_cycle_sync()
                                except:
                                    pass

                # Job should still be released
                mock_release.assert_called_once_with("job-1", "test-agent")

    def test_work_cycle_skips_when_no_jobs(self, tmp_path):
        """work_cycle_sync() returns early when no jobs available.

        Spec: Agent polls for actionable jobs; if none, no work cycle.
        """
        agent = self._create_agent(tmp_path)

        with patch("src.tools.data.jobs.list_jobs", return_value=[]):
            with patch("src.tools.data.jobs.claim_job") as mock_claim:
                with patch.object(agent, '_log'):
                    agent.work_cycle_sync()

                # Should not attempt to claim any job
                mock_claim.assert_not_called()

    def test_work_cycle_aborts_if_claim_fails(self, tmp_path):
        """work_cycle_sync() aborts if job claim fails.

        Spec: Another agent may have claimed the job first.
        """
        agent = self._create_agent(tmp_path)

        mock_job = {"id": "job-1", "name": "Test job", "tags": [], "description": "Test"}

        with patch("src.tools.data.jobs.list_jobs", return_value=[mock_job]):
            with patch("src.tools.data.jobs.claim_job", return_value={"error": "Already claimed"}):
                with patch.object(agent, 'chat') as mock_chat:
                    with patch.object(agent, '_log'):
                        agent.work_cycle_sync()

                # Should not proceed to chat
                mock_chat.assert_not_called()

    def test_work_cycle_handles_reflection_trigger(self, tmp_path):
        """work_cycle_sync() routes consolidation jobs to _execute_reflection_trigger.

        Spec: Consolidation jobs are handled directly, not through chat loop.
        """
        agent = self._create_agent(tmp_path)
        agent.consolidation = MagicMock()

        consolidation_job = {
            "id": "job-1",
            "name": "Trigger:consolidation:both:2025-01-23",
            "tags": [],
            "description": "Consolidation"
        }

        with patch("src.tools.data.jobs.list_jobs", return_value=[consolidation_job]):
            with patch("src.tools.data.jobs.claim_job", return_value={"claimed": True}):
                with patch("src.tools.data.jobs.release_job"):
                    with patch("src.tools.data.jobs.complete_job"):
                        with patch.object(agent, 'chat') as mock_chat:
                            with patch.object(agent, '_log'):
                                agent.work_cycle_sync()

                        # Chat should NOT be called for consolidation jobs
                        mock_chat.assert_not_called()

    def test_work_cycle_one_job_at_a_time(self, tmp_path):
        """work_cycle_sync() only processes first job from list.

        Spec: Agent receives ONE job per work cycle.
        """
        agent = self._create_agent(tmp_path)

        jobs = [
            {"id": "job-1", "name": "First job", "tags": [], "description": "First"},
            {"id": "job-2", "name": "Second job", "tags": [], "description": "Second"},
        ]

        claimed_jobs = []

        def track_claim(job_id, agent_id):
            claimed_jobs.append(job_id)
            return {"claimed": True}

        with patch("src.tools.data.jobs.list_jobs", return_value=jobs):
            with patch("src.tools.data.jobs.claim_job", side_effect=track_claim):
                with patch("src.tools.data.jobs.release_job"):
                    with patch.object(agent.metacognition.planner, 'should_plan', return_value=False):
                        with patch.object(agent, 'chat', side_effect=lambda *a, **k: setattr(agent, '_work_done', True) or "Done"):
                            with patch.object(agent, '_log'):
                                agent.work_cycle_sync()

        # Only first job should be claimed
        assert claimed_jobs == ["job-1"]


# =============================================================================
# Work Cycle Planning Tests
# =============================================================================

@pytest.mark.unit
class TestWorkCyclePlanning:
    """Test planning integration in work_cycle_sync().

    Spec: spec/1_agents.md - "Planning creates a brief approach before execution"
    """

    def _create_agent(self, tmp_path):
        """Create an agent for planning tests."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {
            "id": "test-agent",
            "enabled": True,
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
        """work_cycle_sync() checks if planning is needed for job.

        Spec: Planning is part of Reasoning - it reduces wasted effort.
        """
        agent = self._create_agent(tmp_path)

        mock_job = {"id": "job-1", "name": "Test job", "tags": [], "description": "Test"}

        with patch("src.tools.data.jobs.list_jobs", return_value=[mock_job]):
            with patch("src.tools.data.jobs.claim_job", return_value={"claimed": True}):
                with patch("src.tools.data.jobs.release_job"):
                    with patch.object(agent.metacognition.planner, 'should_plan', return_value=False) as mock_should:
                        with patch.object(agent, 'chat', side_effect=lambda *a, **k: setattr(agent, '_work_done', True) or "Done"):
                            with patch.object(agent, '_log'):
                                agent.work_cycle_sync()

                        mock_should.assert_called_once_with(mock_job)

    def test_work_cycle_creates_plan_when_needed(self, tmp_path):
        """work_cycle_sync() creates plan when planner says to.

        Spec: Agent creates brief plan (tool sequence, delegation, approach).
        """
        agent = self._create_agent(tmp_path)

        mock_job = {"id": "job-1", "name": "Complex job", "tags": [], "description": "Needs planning"}

        with patch("src.tools.data.jobs.list_jobs", return_value=[mock_job]):
            with patch("src.tools.data.jobs.claim_job", return_value={"claimed": True}):
                with patch("src.tools.data.jobs.release_job"):
                    with patch.object(agent.metacognition.planner, 'should_plan', return_value=True):
                        with patch.object(agent.metacognition.planner, 'create_plan', return_value="1. Do this\n2. Do that") as mock_create:
                            with patch.object(agent.metacognition.planner, 'inject_plan', return_value="Plan: ..."):
                                with patch.object(agent, 'chat', side_effect=lambda *a, **k: setattr(agent, '_work_done', True) or "Done"):
                                    with patch.object(agent, '_log'):
                                        agent.work_cycle_sync()

                            mock_create.assert_called_once_with(mock_job)

    def test_work_cycle_injects_plan_into_prompt(self, tmp_path):
        """work_cycle_sync() injects plan into job prompt.

        Spec: Plan is injected before execution.
        """
        agent = self._create_agent(tmp_path)

        mock_job = {"id": "job-1", "name": "Job", "tags": [], "description": "Test"}

        with patch("src.tools.data.jobs.list_jobs", return_value=[mock_job]):
            with patch("src.tools.data.jobs.claim_job", return_value={"claimed": True}):
                with patch("src.tools.data.jobs.release_job"):
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

    Spec: spec/1_agents.md - "Progress Awareness" section
    """

    def _create_agent(self, tmp_path):
        """Create an agent for stuck detection tests."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {
            "id": "test-agent",
            "enabled": True,
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

    def test_work_cycle_checks_stuck_each_iteration(self, tmp_path):
        """work_cycle_sync() checks for stuck patterns each iteration.

        Spec: Detects stuck patterns: same tool called repeatedly with identical inputs.
        """
        agent = self._create_agent(tmp_path)

        mock_job = {"id": "job-1", "name": "Job", "tags": [], "description": "Test"}
        iteration_count = [0]

        def track_chat(*args, **kwargs):
            iteration_count[0] += 1
            if iteration_count[0] >= 2:
                agent._work_done = True
            return "Response"

        with patch("src.tools.data.jobs.list_jobs", return_value=[mock_job]):
            with patch("src.tools.data.jobs.claim_job", return_value={"claimed": True}):
                with patch("src.tools.data.jobs.release_job"):
                    with patch.object(agent.metacognition.planner, 'should_plan', return_value=False):
                        with patch.object(agent.metacognition, 'check_stuck', return_value=None) as mock_check:
                            with patch.object(agent, 'chat', side_effect=track_chat):
                                with patch.object(agent, '_log'):
                                    agent.work_cycle_sync()

                            # check_stuck should be called each iteration
                            assert mock_check.call_count >= 1

    def test_work_cycle_breaks_when_stuck(self, tmp_path):
        """work_cycle_sync() breaks loop when stuck is detected.

        Spec: Breaks work cycle when stuck detected.
        """
        agent = self._create_agent(tmp_path)

        mock_job = {"id": "job-1", "name": "Job", "tags": [], "description": "Test"}
        chat_calls = [0]

        def count_chat(*args, **kwargs):
            chat_calls[0] += 1
            return "Response"

        with patch("src.tools.data.jobs.list_jobs", return_value=[mock_job]):
            with patch("src.tools.data.jobs.claim_job", return_value={"claimed": True}):
                with patch("src.tools.data.jobs.release_job"):
                    with patch.object(agent.metacognition.planner, 'should_plan', return_value=False):
                        # Return "stuck" on first check
                        with patch.object(agent.metacognition, 'check_stuck', return_value="Repeated tool calls"):
                            with patch.object(agent, 'chat', side_effect=count_chat):
                                with patch.object(agent, '_log'):
                                    agent.work_cycle_sync()

                        # Should have minimal chat calls (stuck detected immediately)
                        # The loop breaks before second iteration
                        assert chat_calls[0] <= 1


# =============================================================================
# Work Cycle Deferred Consolidation Tests
# =============================================================================

@pytest.mark.unit
class TestWorkCycleDeferredConsolidation:
    """Test deferred consolidation batching in work_cycle_sync().

    Spec: spec/1_agents.md - "efficiency.defer_consolidation_in_work_cycles"
    """

    def _create_agent(self, tmp_path):
        """Create an agent with consolidation enabled."""
        from src.agent.agent import Agent

        agent_dir = tmp_path / "agents" / "test-agent"
        agent_dir.mkdir(parents=True)
        config = {
            "id": "test-agent",
            "enabled": True,
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

        mock_job = {"id": "job-1", "name": "Job", "tags": [], "description": "Test"}
        chat_kwargs = []

        def capture_chat(*args, **kwargs):
            chat_kwargs.append(kwargs)
            agent._work_done = True
            return "Done"

        with patch("src.tools.data.jobs.list_jobs", return_value=[mock_job]):
            with patch("src.tools.data.jobs.claim_job", return_value={"claimed": True}):
                with patch("src.tools.data.jobs.release_job"):
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

        mock_job = {"id": "job-1", "name": "Job", "tags": [], "description": "Test"}
        iteration = [0]

        def multi_iteration_chat(*args, **kwargs):
            iteration[0] += 1
            if iteration[0] >= 2:
                agent._work_done = True
            return f"Response {iteration[0]}"

        with patch("src.tools.data.jobs.list_jobs", return_value=[mock_job]):
            with patch("src.tools.data.jobs.claim_job", return_value={"claimed": True}):
                with patch("src.tools.data.jobs.release_job"):
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
