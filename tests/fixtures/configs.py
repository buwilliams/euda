"""
Configuration test fixtures and factories.
"""

from typing import Optional


def create_system_config(
    budget_limit: float = 10.0,
    input_pricing: float = 3.0,
    output_pricing: float = 15.0,
    warning_percent: int = 80,
    pause_percent: int = 100,
    token_awareness_enabled: bool = True,
    **overrides
) -> dict:
    """Create a system configuration for testing.

    Args:
        budget_limit: Monthly budget in dollars
        input_pricing: Price per million input tokens
        output_pricing: Price per million output tokens
        warning_percent: Threshold for warning
        pause_percent: Threshold for pause
        token_awareness_enabled: Whether token awareness is active
        **overrides: Additional config overrides

    Returns:
        System configuration dictionary
    """
    config = {
        "llm": {
            "budget": {"limit": budget_limit},
            "default_pricing": {
                "input": input_pricing,
                "cached_input": input_pricing / 10,
                "output": output_pricing
            }
        },
        "metacognition": {
            "token_awareness": {
                "enabled": token_awareness_enabled,
                "thresholds": {
                    "warning_percent": warning_percent,
                    "pause_percent": pause_percent
                }
            }
        }
    }

    # Deep merge overrides
    for key, value in overrides.items():
        if isinstance(value, dict) and key in config:
            config[key].update(value)
        else:
            config[key] = value

    return config


def create_token_budget_config(
    frequency: str = "daily",
    input_ratio: float = 0.8,
    output_ratio: float = 0.2
) -> dict:
    """Create a token budget configuration for an agent.

    Args:
        frequency: Budget frequency (hourly, daily, weekly, monthly)
        input_ratio: Fraction of budget for input tokens
        output_ratio: Fraction of budget for output tokens

    Returns:
        Token budget configuration dictionary
    """
    return {
        "frequency": frequency,
        "input_ratio": input_ratio,
        "output_ratio": output_ratio
    }
