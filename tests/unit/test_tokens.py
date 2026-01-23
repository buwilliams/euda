"""
Unit tests for token awareness module.

Tests for src/agent/cognition/metacognition/regulation/tokens.py
"""

import json
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock


class TestTokenAwarenessAcquire:
    """Test acquire() method for pre-call token checks."""

    def test_acquire_succeeds_under_budget(self, create_test_agent, fresh_token_awareness):
        """acquire() should succeed when under budget."""
        create_test_agent("test-agent")
        ta = fresh_token_awareness

        # Small request should succeed
        result = ta.acquire("test-agent", estimated_input_tokens=100, enabled_agent_count=1)
        assert result is True

    def test_acquire_tracks_cumulative_usage(self, create_test_agent, fresh_token_awareness):
        """Multiple acquires should track cumulative usage."""
        create_test_agent("test-agent")
        ta = fresh_token_awareness

        # Make multiple small acquisitions
        for _ in range(5):
            ta.acquire("test-agent", estimated_input_tokens=100, enabled_agent_count=1)

        # Usage should be tracked (though acquire doesn't actually record)
        # This just verifies no errors on repeated calls
        usage = ta.get_agent_usage("test-agent")
        assert usage["agent_id"] == "test-agent"

    def test_acquire_with_token_awareness_disabled(self, create_test_agent, patch_data_dir):
        """acquire() should always succeed when token awareness is disabled."""
        from src.agent.cognition.metacognition.regulation import tokens

        # Disable token awareness in config
        config_path = patch_data_dir / "system" / "config.json"
        config = json.loads(config_path.read_text())
        config["metacognition"]["token_awareness"]["enabled"] = False
        config_path.write_text(json.dumps(config))

        # Reset singleton to pick up new config
        tokens._token_awareness = None
        ta = tokens.get_token_awareness()

        create_test_agent("test-agent")

        # Even huge request should succeed
        result = ta.acquire("test-agent", estimated_input_tokens=999999999, enabled_agent_count=1)
        assert result is True


class TestTokenAwarenessRecord:
    """Test record() method for post-call token recording."""

    def test_record_updates_usage(self, create_test_agent, fresh_token_awareness):
        """record() should update cumulative usage."""
        create_test_agent("test-agent")
        ta = fresh_token_awareness

        ta.record(
            "test-agent",
            input_tokens=1000,
            output_tokens=500,
            enabled_agent_count=1
        )

        usage = ta.get_agent_usage("test-agent")
        assert usage["input_tokens"] == 1000
        assert usage["output_tokens"] == 500

    def test_record_accumulates_usage(self, create_test_agent, fresh_token_awareness):
        """Multiple records should accumulate usage."""
        create_test_agent("test-agent")
        ta = fresh_token_awareness

        ta.record("test-agent", input_tokens=100, output_tokens=50, enabled_agent_count=1)
        ta.record("test-agent", input_tokens=200, output_tokens=100, enabled_agent_count=1)

        usage = ta.get_agent_usage("test-agent")
        assert usage["input_tokens"] == 300
        assert usage["output_tokens"] == 150

    def test_record_persists_to_disk(self, create_test_agent, fresh_token_awareness, patch_data_dir):
        """record() should persist usage data to disk."""
        create_test_agent("test-agent")
        ta = fresh_token_awareness

        ta.record(
            "test-agent",
            input_tokens=1000,
            output_tokens=500,
            enabled_agent_count=1
        )

        # Check usage file exists
        usage_file = patch_data_dir / "system" / "token_usage" / "current.json"
        assert usage_file.exists()

        data = json.loads(usage_file.read_text())
        assert "test-agent" in data.get("agent_usage", {})


class TestTokenAwarenessUsageTracking:
    """Test usage tracking and period management."""

    def test_usage_resets_on_new_period(self, create_test_agent, fresh_token_awareness):
        """Usage should reset when period changes."""
        from freezegun import freeze_time
        from datetime import datetime, timedelta

        create_test_agent("test-agent")
        ta = fresh_token_awareness

        # Record usage "yesterday"
        with freeze_time(datetime.now() - timedelta(days=1)):
            ta.record("test-agent", input_tokens=1000, output_tokens=500, enabled_agent_count=1)

        # Get usage "today" - should be fresh period
        usage = ta._get_agent_usage("test-agent", "daily")

        # Today's period should show 0 (fresh period)
        assert usage["input"] == 0
        assert usage["output"] == 0

    def test_get_all_agent_usage(self, create_test_agent, fresh_token_awareness):
        """get_all_agent_usage should return all tracked agents."""
        ta = fresh_token_awareness

        create_test_agent("agent1")
        create_test_agent("agent2")

        ta.record("agent1", input_tokens=100, output_tokens=50, enabled_agent_count=2)
        ta.record("agent2", input_tokens=200, output_tokens=100, enabled_agent_count=2)

        all_usage = ta.get_all_agent_usage()

        assert "agent1" in all_usage
        assert "agent2" in all_usage
        assert all_usage["agent1"]["input_tokens"] == 100
        assert all_usage["agent2"]["input_tokens"] == 200


class TestTokenAwarenessStateManagement:
    """Test agent state management methods."""

    def test_get_pause_info_when_paused(self, create_test_agent, fresh_token_awareness):
        """get_pause_info should return details for paused agents."""
        from src.agent.cognition.metacognition.regulation.tokens import AgentState

        create_test_agent("test-agent")
        ta = fresh_token_awareness

        ta.set_agent_state("test-agent", AgentState.PAUSED, "test reason")

        info = ta.get_pause_info("test-agent")
        assert info["is_paused"] is True
        assert info["reason"] == "test reason"
        assert info["timestamp"] is not None

    def test_get_pause_info_when_not_paused(self, create_test_agent, fresh_token_awareness):
        """get_pause_info should return is_paused=False for active agents."""
        create_test_agent("test-agent")
        ta = fresh_token_awareness

        info = ta.get_pause_info("test-agent")
        assert info["is_paused"] is False

    def test_invalidate_config(self, fresh_token_awareness):
        """invalidate_config should clear cached configuration."""
        ta = fresh_token_awareness

        # Load config to populate cache
        ta._load_config()
        assert ta._config_cache is not None

        # Invalidate
        ta.invalidate_config()

        assert ta._config_cache is None
        assert ta._config_mtime == 0


class TestCostCalculation:
    """Test cost calculation methods."""

    def test_calculate_cost_basic(self, fresh_token_awareness):
        """Cost calculation should use pricing from config."""
        ta = fresh_token_awareness

        # Default pricing: input=3.0, output=15.0 per million
        cost = ta._calculate_cost(
            provider="openai",
            input_tokens=1_000_000,  # 1M tokens
            output_tokens=100_000    # 100K tokens
        )

        # 1M input at $3/M = $3, 100K output at $15/M = $1.5
        expected = 3.0 + 1.5
        assert abs(cost - expected) < 0.01

    def test_calculate_cost_with_cache(self, fresh_token_awareness):
        """Cost calculation should discount cached input tokens."""
        ta = fresh_token_awareness

        # With caching: cached_input at 0.3, regular input at 3.0
        cost = ta._calculate_cost(
            provider="openai",
            input_tokens=1_000_000,      # Total prompt tokens
            output_tokens=0,
            cached_input_tokens=500_000  # Half cached
        )

        # 500K non-cached at $3/M = $1.5, 500K cached at $0.3/M = $0.15
        expected = 1.5 + 0.15
        assert abs(cost - expected) < 0.01

    def test_get_cost_summary(self, create_test_agent, fresh_token_awareness):
        """get_cost_summary should aggregate costs by agent."""
        create_test_agent("test-agent")
        ta = fresh_token_awareness

        # Record some usage
        ta.record("test-agent", input_tokens=1000, output_tokens=500, enabled_agent_count=1)

        summary = ta.get_cost_summary(days=30)

        assert "agents" in summary
        assert "total_cost" in summary
        assert "total_calls" in summary


class TestThreadSafety:
    """Test thread safety of token awareness."""

    def test_concurrent_record_calls(self, create_test_agent, fresh_token_awareness):
        """Concurrent record() calls should be thread-safe."""
        import threading

        create_test_agent("test-agent")
        ta = fresh_token_awareness

        errors = []

        def record_usage():
            try:
                for _ in range(10):
                    ta.record("test-agent", input_tokens=100, output_tokens=50, enabled_agent_count=1)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_usage) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors: {errors}"

        # All records should be accumulated
        usage = ta.get_agent_usage("test-agent")
        assert usage["input_tokens"] == 50 * 100  # 5 threads * 10 iterations * 100 tokens
