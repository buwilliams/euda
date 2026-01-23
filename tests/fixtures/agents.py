"""
Agent test fixtures and factories.
"""

from typing import Optional, List


def create_test_agent_config(
    agent_id: str = "test-agent",
    name: str = None,
    enabled: bool = True,
    state: str = "enabled",
    tools: List[str] = None,
    triggers: List[str] = None,
    token_budget: dict = None,
    **overrides
) -> dict:
    """Create an agent configuration dictionary for testing.

    Args:
        agent_id: Unique agent identifier
        name: Display name (defaults to formatted agent_id)
        enabled: Whether agent is enabled
        state: Agent state (enabled, disabled, paused)
        tools: List of tool names the agent can use
        triggers: List of trigger patterns
        token_budget: Token budget configuration
        **overrides: Additional fields to override

    Returns:
        Agent configuration dictionary
    """
    config = {
        "id": agent_id,
        "name": name or agent_id.title().replace("-", " "),
        "enabled": enabled,
        "state": state,
        "tools": tools or ["list_jobs", "get_job", "create_job", "complete_job"],
        "triggers": triggers or ["job:assigned"],
        "token_budget": token_budget or {
            "frequency": "daily",
            "input_ratio": 0.8,
            "output_ratio": 0.2
        }
    }
    config.update(overrides)
    return config


def create_paused_agent_config(agent_id: str = "paused-agent", reason: str = "threshold exceeded") -> dict:
    """Create a paused agent configuration."""
    return create_test_agent_config(
        agent_id=agent_id,
        enabled=False,
        state="paused",
        pause_reason=reason
    )


def create_disabled_agent_config(agent_id: str = "disabled-agent") -> dict:
    """Create a disabled agent configuration."""
    return create_test_agent_config(
        agent_id=agent_id,
        enabled=False,
        state="disabled"
    )
