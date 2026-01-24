"""
Configuration test fixtures and factories.
"""

from typing import Optional


def create_system_config(**overrides) -> dict:
    """Create a system configuration for testing.

    Note: LLM settings (including budget thresholds) are now in llm.json, not config.json.

    Args:
        **overrides: Additional config overrides

    Returns:
        System configuration dictionary
    """
    config = {
        "metacognition": {}
    }

    # Deep merge overrides
    for key, value in overrides.items():
        if isinstance(value, dict) and key in config:
            config[key].update(value)
        else:
            config[key] = value

    return config


def create_llm_config(
    provider: str = "openai",
    model: str = "gpt-4.1",
    budget_limit: float = 10.0,
    warning_percent: int = 80,
    pause_percent: int = 100,
    input_pricing: float = 3.0,
    output_pricing: float = 15.0,
    **overrides
) -> dict:
    """Create an LLM configuration for testing.

    Args:
        provider: LLM provider (openai, anthropic, xai)
        model: Model name
        budget_limit: Monthly budget in dollars
        warning_percent: Threshold for warning (default 80%)
        pause_percent: Threshold for pause (default 100%)
        input_pricing: Price per million input tokens
        output_pricing: Price per million output tokens
        **overrides: Additional config overrides

    Returns:
        LLM configuration dictionary
    """
    config = {
        "provider": provider,
        "model": model,
        "budget": {"limit": budget_limit, "period": "monthly", "warning_percent": warning_percent, "pause_percent": pause_percent},
        "providers": {
            "openai": {
                "display_name": "ChatGPT",
                "description": "OpenAI's GPT models",
                "models": [
                    {"model": "gpt-4.1", "display_name": "GPT-4.1", "pricing": {"input": input_pricing, "cached_input": input_pricing / 10, "output": output_pricing}}
                ]
            },
            "anthropic": {
                "display_name": "Claude",
                "description": "Anthropic's Claude models",
                "models": [
                    {"model": "claude-sonnet-4", "display_name": "Claude Sonnet 4", "pricing": {"input": input_pricing, "cached_input": input_pricing / 10, "output": output_pricing}}
                ]
            },
            "xai": {
                "display_name": "Grok",
                "description": "xAI's Grok models",
                "models": [
                    {"model": "grok-4-1-fast-reasoning", "display_name": "Grok 4.1 Fast", "pricing": {"input": 0.2, "cached_input": 0.02, "output": 0.5}}
                ]
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
