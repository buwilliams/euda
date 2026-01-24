"""
Token Budget Enforcement Invariant Tests.

Spec: specs/1_agents.md lines 236-262

These tests verify the token budget system that prevents runaway costs.

Invariants tested:
- acquire() raises at 100% pause threshold
- record() pauses agent when output threshold exceeded
- Budget splits equally among enabled agents
- Warning recorded but no pause at 80%
- Daily frequency divides monthly by 31
"""

import json
import pytest


@pytest.mark.invariant
class TestTokenBudgetEnforcement:
    """Test token budget enforcement invariants from spec."""

    def test_acquire_raises_at_pause_threshold(self, create_test_agent, fresh_token_awareness):
        """acquire() should raise AgentPausedError at 100% threshold.

        Spec: Token awareness auto-pauses at pause_percent (default 100%).
        """
        from src.agent.cognition.metacognition.regulation.tokens import AgentPausedError

        # Create agent with very small budget (1 token per period for testing)
        config = create_test_agent("budget-agent")
        ta = fresh_token_awareness

        # Get the calculated budget to know how much to request
        # Agent count is determined internally by _count_budget_agents()
        agent_count = ta._count_budget_agents()
        budget_config = ta._get_agent_budget_config("budget-agent")
        total_budget, _ = ta._calculate_period_budget(agent_count, budget_config.frequency)
        input_budget = int(total_budget * budget_config.input_ratio)

        # Request exactly the budget - should raise at 100%
        with pytest.raises(AgentPausedError) as exc_info:
            ta.acquire("budget-agent", estimated_input_tokens=input_budget)

        assert "threshold exceeded" in str(exc_info.value).lower()

    def test_record_pauses_on_output_exceeded(self, create_test_agent, fresh_token_awareness):
        """record() should pause agent when output threshold exceeded.

        Spec: Post-call recording checks output budget and pauses if exceeded.
        """
        from src.agent.cognition.metacognition.regulation.tokens import AgentState

        config = create_test_agent("output-agent")
        ta = fresh_token_awareness

        # Get the calculated budget
        # Agent count is determined internally by _count_budget_agents()
        agent_count = ta._count_budget_agents()
        budget_config = ta._get_agent_budget_config("output-agent")
        total_budget, _ = ta._calculate_period_budget(agent_count, budget_config.frequency)
        output_budget = int(total_budget * budget_config.output_ratio)

        # Record output that exceeds budget
        ta.record(
            "output-agent",
            input_tokens=100,
            output_tokens=output_budget + 1  # Exceed output budget
        )

        state = ta.get_agent_state("output-agent")
        assert state == AgentState.PAUSED

    def test_budget_splits_among_enabled(self, create_test_agent, fresh_token_awareness):
        """Budget should split equally among enabled agents.

        Spec: Each agent gets global_budget / enabled_count.
        """
        ta = fresh_token_awareness

        # Calculate budget for 1 agent
        budget_1, _ = ta._calculate_period_budget(1, "daily")

        # Calculate budget for 3 agents
        budget_3, _ = ta._calculate_period_budget(3, "daily")

        # Budget for 3 agents should be 1/3 of single agent budget
        assert budget_3 == budget_1 // 3

    def test_warning_no_pause_at_80_percent(self, create_test_agent, fresh_token_awareness):
        """Warning should be recorded but no pause at 80% threshold.

        Spec: warning_percent triggers logging but not pause.
        """
        from src.agent.cognition.metacognition.regulation.tokens import AgentState

        config = create_test_agent("warning-agent")
        ta = fresh_token_awareness

        # Get budget and calculate 80%
        # Agent count is determined internally by _count_budget_agents()
        agent_count = ta._count_budget_agents()
        budget_config = ta._get_agent_budget_config("warning-agent")
        total_budget, _ = ta._calculate_period_budget(agent_count, budget_config.frequency)
        input_budget = int(total_budget * budget_config.input_ratio)
        warning_amount = int(input_budget * 0.80)

        # Acquire 80% - should succeed without pause
        result = ta.acquire("warning-agent", estimated_input_tokens=warning_amount - 1)
        assert result is True

        state = ta.get_agent_state("warning-agent")
        assert state == AgentState.ENABLED

    def test_frequency_daily_divides_by_31(self, fresh_token_awareness):
        """Daily frequency should divide monthly budget by 31.

        Spec: daily = monthly / 31
        """
        ta = fresh_token_awareness

        monthly_budget, _ = ta._calculate_period_budget(1, "monthly")
        daily_budget, _ = ta._calculate_period_budget(1, "daily")

        assert daily_budget == monthly_budget // 31

    def test_frequency_weekly_divides_by_4(self, fresh_token_awareness):
        """Weekly frequency should divide monthly budget by 4.

        Spec: weekly = monthly / 4
        """
        ta = fresh_token_awareness

        monthly_budget, _ = ta._calculate_period_budget(1, "monthly")
        weekly_budget, _ = ta._calculate_period_budget(1, "weekly")

        assert weekly_budget == monthly_budget // 4

    def test_frequency_hourly_divides_daily_by_24(self, fresh_token_awareness):
        """Hourly frequency should divide daily budget by 24.

        Spec: hourly = daily / 24
        """
        ta = fresh_token_awareness

        daily_budget, _ = ta._calculate_period_budget(1, "daily")
        hourly_budget, _ = ta._calculate_period_budget(1, "hourly")

        assert hourly_budget == daily_budget // 24


@pytest.mark.invariant
class TestBudgetConfiguration:
    """Test budget configuration loading and defaults."""

    def test_default_budget_frequency(self, fresh_token_awareness):
        """Default budget frequency should be daily.

        Spec: Agents default to daily budget frequency.
        """
        ta = fresh_token_awareness

        # Agent without explicit config should get default
        budget_config = ta._get_agent_budget_config("nonexistent-agent")

        assert budget_config.frequency == "daily"

    def test_default_input_output_ratio(self, fresh_token_awareness):
        """Default input/output ratio should be 80/20.

        Spec: 80% of budget for input, 20% for output.
        """
        ta = fresh_token_awareness

        budget_config = ta._get_agent_budget_config("nonexistent-agent")

        assert budget_config.input_ratio == 0.8
        assert budget_config.output_ratio == 0.2

    def test_custom_budget_config(self, create_test_agent, fresh_token_awareness):
        """Agent can override default budget configuration.

        Spec: Per-agent budget configuration in config.json.
        """
        custom_budget = {
            "frequency": "hourly",
            "input_ratio": 0.7,
            "output_ratio": 0.3,
            "consumes_tokens": True
        }
        create_test_agent("custom-agent", token_budget=custom_budget)
        ta = fresh_token_awareness

        budget_config = ta._get_agent_budget_config("custom-agent")

        assert budget_config.frequency == "hourly"
        assert budget_config.input_ratio == 0.7
        assert budget_config.output_ratio == 0.3
        assert budget_config.consumes_tokens is True


@pytest.mark.invariant
class TestPeriodKeyGeneration:
    """Test period key generation for usage tracking."""

    def test_period_key_monthly(self, fresh_token_awareness):
        """Monthly period key should be YYYY-MM format."""
        ta = fresh_token_awareness
        from datetime import datetime

        key = ta._get_period_key("monthly")
        now = datetime.now()

        assert key == now.strftime("%Y-%m")

    def test_period_key_weekly(self, fresh_token_awareness):
        """Weekly period key should be YYYY-Wnn format."""
        ta = fresh_token_awareness
        from datetime import datetime

        key = ta._get_period_key("weekly")
        now = datetime.now()

        expected = f"{now.year}-W{now.isocalendar()[1]:02d}"
        assert key == expected

    def test_period_key_daily(self, fresh_token_awareness):
        """Daily period key should be YYYY-MM-DD format."""
        ta = fresh_token_awareness
        from datetime import datetime

        key = ta._get_period_key("daily")
        now = datetime.now()

        assert key == now.strftime("%Y-%m-%d")

    def test_period_key_hourly(self, fresh_token_awareness):
        """Hourly period key should be YYYY-MM-DD-HH format."""
        ta = fresh_token_awareness
        from datetime import datetime

        key = ta._get_period_key("hourly")
        now = datetime.now()

        assert key == now.strftime("%Y-%m-%d-%H")


@pytest.mark.invariant
class TestConsumesTokensExclusion:
    """Test that agents with consumes_tokens=false are excluded from budget calculations."""

    def test_non_consuming_agent_excluded_from_count(self, create_test_agent, fresh_token_awareness):
        """Agents with consumes_tokens=false should not be counted in budget sharing.

        Spec: User agent doesn't consume tokens, shouldn't affect other agents' budgets.
        """
        ta = fresh_token_awareness

        # Create two normal agents
        create_test_agent("agent1")
        create_test_agent("agent2")

        count_before = ta._count_budget_agents()

        # Create a non-consuming agent (like user agent)
        create_test_agent("non-consumer", token_budget={"consumes_tokens": False})

        count_after = ta._count_budget_agents()

        # Count should not change when adding non-consuming agent
        assert count_after == count_before

    def test_consuming_agent_included_in_count(self, create_test_agent, fresh_token_awareness):
        """Agents with consumes_tokens=true (default) should be counted."""
        ta = fresh_token_awareness

        # Create a baseline agent first (to avoid the max(1, 0) = 1 edge case)
        create_test_agent("baseline")
        count_before = ta._count_budget_agents()

        # Create another normal consuming agent
        create_test_agent("consumer", token_budget={"consumes_tokens": True})

        count_after = ta._count_budget_agents()

        # Count should increase by 1
        assert count_after == count_before + 1

    def test_default_consumes_tokens_is_true(self, create_test_agent, fresh_token_awareness):
        """Agents without explicit consumes_tokens should default to True."""
        ta = fresh_token_awareness

        # Create agent without consumes_tokens field
        create_test_agent("default-agent", token_budget={"frequency": "daily"})

        budget_config = ta._get_agent_budget_config("default-agent")

        assert budget_config.consumes_tokens is True

    def test_get_agent_usage_includes_consumes_tokens(self, create_test_agent, fresh_token_awareness):
        """get_agent_usage should return consumes_tokens in the response."""
        ta = fresh_token_awareness

        # Create non-consuming agent
        create_test_agent("non-consumer", token_budget={"consumes_tokens": False})

        usage = ta.get_agent_usage("non-consumer")

        assert "consumes_tokens" in usage
        assert usage["consumes_tokens"] is False

    def test_budget_increases_when_non_consumer_excluded(self, create_test_agent, fresh_token_awareness):
        """Budget per agent should increase when non-consuming agents are excluded.

        With fewer agents sharing the budget, each consuming agent gets more.
        """
        ta = fresh_token_awareness

        # Create one consuming agent
        create_test_agent("consumer1")
        budget_with_one, _ = ta._calculate_period_budget(ta._count_budget_agents(), "daily")

        # Create another consuming agent - budget should decrease
        create_test_agent("consumer2")
        budget_with_two, _ = ta._calculate_period_budget(ta._count_budget_agents(), "daily")

        assert budget_with_two < budget_with_one

        # Add non-consuming agent - budget should NOT change
        create_test_agent("non-consumer", token_budget={"consumes_tokens": False})
        budget_with_non_consumer, _ = ta._calculate_period_budget(ta._count_budget_agents(), "daily")

        assert budget_with_non_consumer == budget_with_two
