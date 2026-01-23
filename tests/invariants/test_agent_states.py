"""
Agent State Transition Invariant Tests.

Spec: docs/3_system.md lines 78-85, specs/1_agents.md lines 219-233

These tests verify the agent state machine and transition rules.

State Machine:
- enabled: Normal operation
- paused: Threshold breach - requires manual intervention to resume
- disabled: User explicitly disabled

Invariants tested:
- Only system can auto-pause (threshold breach)
- Paused agents require manual resume
- Any state can be disabled by user
- Disabled agents raise AgentPausedError on acquire()
- State changes persist to config.json
"""

import json
import pytest


@pytest.mark.invariant
class TestAgentStateTransitions:
    """Test agent state transition invariants from spec."""

    def test_enabled_to_paused_by_system(self, create_test_agent, fresh_token_awareness):
        """System can pause an enabled agent (e.g., threshold breach).

        Spec: Token awareness auto-pauses agents when thresholds exceeded.
        """
        from src.agent.cognition.metacognition.regulation.tokens import AgentState

        config = create_test_agent("test-agent", state="enabled")
        ta = fresh_token_awareness

        # System pauses agent
        ta.set_agent_state("test-agent", AgentState.PAUSED, "threshold exceeded")

        state = ta.get_agent_state("test-agent")
        assert state == AgentState.PAUSED

    def test_paused_to_enabled_manual(self, create_test_agent, fresh_token_awareness):
        """Paused agents can be resumed manually.

        Spec: Paused state requires manual intervention.
        """
        from src.agent.cognition.metacognition.regulation.tokens import AgentState

        config = create_test_agent("test-agent", state="paused")
        ta = fresh_token_awareness

        # First set to paused
        ta.set_agent_state("test-agent", AgentState.PAUSED, "threshold exceeded")

        # Then resume
        ta.enable_agent("test-agent")

        state = ta.get_agent_state("test-agent")
        assert state == AgentState.ENABLED

    def test_any_to_disabled_user_explicit(self, create_test_agent, fresh_token_awareness):
        """Any state can transition to disabled.

        Spec: User can disable any agent at any time.
        """
        from src.agent.cognition.metacognition.regulation.tokens import AgentState

        ta = fresh_token_awareness

        # From enabled
        create_test_agent("agent1", state="enabled")
        ta.disable_agent("agent1")
        assert ta.get_agent_state("agent1") == AgentState.DISABLED

        # From paused
        create_test_agent("agent2", state="paused")
        ta.set_agent_state("agent2", AgentState.PAUSED, "test")
        ta.disable_agent("agent2")
        assert ta.get_agent_state("agent2") == AgentState.DISABLED

    def test_disabled_agents_reject_acquire(self, create_test_agent, fresh_token_awareness):
        """Disabled agents should raise AgentPausedError on acquire().

        Spec: Disabled agents cannot perform LLM calls.
        """
        from src.agent.cognition.metacognition.regulation.tokens import (
            AgentState, AgentPausedError
        )

        config = create_test_agent("disabled-agent", state="disabled", enabled=False)
        ta = fresh_token_awareness

        with pytest.raises(AgentPausedError) as exc_info:
            ta.acquire("disabled-agent", estimated_input_tokens=1000)

        assert "disabled" in str(exc_info.value).lower()

    def test_paused_agents_reject_acquire(self, create_test_agent, fresh_token_awareness):
        """Paused agents should raise AgentPausedError on acquire().

        Spec: Paused agents cannot perform LLM calls until resumed.
        """
        from src.agent.cognition.metacognition.regulation.tokens import (
            AgentState, AgentPausedError
        )

        config = create_test_agent("paused-agent", state="paused", enabled=False)
        ta = fresh_token_awareness
        ta.set_agent_state("paused-agent", AgentState.PAUSED, "test")

        with pytest.raises(AgentPausedError) as exc_info:
            ta.acquire("paused-agent", estimated_input_tokens=1000)

        assert "paused-agent" in str(exc_info.value)

    def test_state_persists_to_config(self, create_test_agent, fresh_token_awareness, patch_data_dir):
        """State changes should be saved to config.json.

        Spec: Agent state persists across restarts.
        """
        from src.agent.cognition.metacognition.regulation.tokens import AgentState

        config = create_test_agent("persist-agent", state="enabled")
        ta = fresh_token_awareness

        # Change state
        ta.set_agent_state("persist-agent", AgentState.PAUSED, "test reason")

        # Read config from disk
        config_path = patch_data_dir / "agents" / "persist-agent" / "config.json"
        saved_config = json.loads(config_path.read_text())

        assert saved_config["state"] == "paused"
        assert saved_config["pause_reason"] == "test reason"
        assert saved_config["pause_timestamp"] is not None

    def test_enable_clears_pause_info(self, create_test_agent, fresh_token_awareness, patch_data_dir):
        """Enabling an agent should clear pause info from config.

        Spec: Resume clears the pause reason and timestamp.
        """
        from src.agent.cognition.metacognition.regulation.tokens import AgentState

        config = create_test_agent("resume-agent", state="paused")
        ta = fresh_token_awareness

        # Set to paused
        ta.set_agent_state("resume-agent", AgentState.PAUSED, "test reason")

        # Resume
        ta.enable_agent("resume-agent")

        # Read config from disk
        config_path = patch_data_dir / "agents" / "resume-agent" / "config.json"
        saved_config = json.loads(config_path.read_text())

        assert saved_config["state"] == "enabled"
        assert saved_config.get("pause_reason") is None
        assert saved_config.get("pause_timestamp") is None


@pytest.mark.invariant
class TestAgentStateEnum:
    """Test AgentState enum values match spec."""

    def test_state_values(self):
        """AgentState enum should have exactly the specified values."""
        from src.agent.cognition.metacognition.regulation.tokens import AgentState

        assert AgentState.ENABLED.value == "enabled"
        assert AgentState.DISABLED.value == "disabled"
        assert AgentState.PAUSED.value == "paused"

        # Ensure no extra states
        assert len(AgentState) == 3
