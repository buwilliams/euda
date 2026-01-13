"""
Rate Limiting API Routes - Status, events, configuration
"""

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ...rate_limiter import get_rate_limiter
from ...logger import get_logger


router = APIRouter()

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
CONFIG_PATH = DATA_DIR / "system" / "config.json"


# ============== Models ==============

class RateLimitingConfigUpdate(BaseModel):
    """Model for updating rate limiting configuration."""
    enabled: Optional[bool] = None
    rolling_window: Optional[dict] = None
    throttle: Optional[dict] = None
    runaway_detection: Optional[dict] = None


# ============== Status ==============

@router.get("/status")
def get_rate_limiting_status():
    """Get current rate limiting status.

    Returns:
        Dict with current status including:
        - enabled: Whether rate limiting is active
        - rolling_window: Config and current call count
        - throttle: Config
        - runaway_detection: Config
        - paused_agents: List of paused agent IDs
        - pause_details: Details for each paused agent
    """
    return get_rate_limiter().get_status()


@router.get("/agents/{agent_id}/stats")
def get_agent_rate_stats(agent_id: str):
    """Get rate limiting stats for a specific agent.

    Args:
        agent_id: ID of the agent

    Returns:
        Dict with agent-specific stats including calls per minute/hour
    """
    return get_rate_limiter().get_agent_stats(agent_id)


# ============== Events ==============

@router.get("/events")
def get_rate_limiting_events(days: int = 1):
    """Get rate limiting event log.

    Args:
        days: Number of days to look back (default 1)

    Returns:
        List of rate limiting events (rate_limit_hit, agent_paused, agent_resumed, etc.)
    """
    logger = get_logger("system/logs/rate-limiting")
    return logger.read_logs(days)


# ============== Agent Control ==============

@router.post("/agents/{agent_id}/resume")
def resume_agent(agent_id: str):
    """Resume a paused agent.

    Args:
        agent_id: ID of the agent to resume

    Returns:
        Dict with resumed status
    """
    rate_limiter = get_rate_limiter()

    if not rate_limiter.is_agent_paused(agent_id):
        return {"resumed": False, "agent_id": agent_id, "error": "Agent is not paused"}

    rate_limiter.resume_agent(agent_id)
    return {"resumed": True, "agent_id": agent_id}


# ============== Configuration ==============

@router.get("/config")
def get_rate_limiting_config():
    """Get current rate limiting configuration.

    Returns:
        Dict with rate limiting configuration from config.json
    """
    if not CONFIG_PATH.exists():
        return {}

    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        return config.get("llm", {}).get("rate_limiting", {})
    except (json.JSONDecodeError, IOError):
        return {}


@router.put("/config")
def update_rate_limiting_config(data: RateLimitingConfigUpdate):
    """Update rate limiting configuration.

    Args:
        data: Configuration updates to apply

    Returns:
        Updated configuration
    """
    if not CONFIG_PATH.exists():
        return {"error": "Config file not found"}

    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return {"error": f"Failed to read config: {e}"}

    # Ensure llm.rate_limiting exists
    if "llm" not in config:
        config["llm"] = {}
    if "rate_limiting" not in config["llm"]:
        config["llm"]["rate_limiting"] = {}

    rate_limiting = config["llm"]["rate_limiting"]

    # Update fields that were provided
    if data.enabled is not None:
        rate_limiting["enabled"] = data.enabled

    if data.rolling_window is not None:
        if "rolling_window" not in rate_limiting:
            rate_limiting["rolling_window"] = {}
        rate_limiting["rolling_window"].update(data.rolling_window)

    if data.throttle is not None:
        if "throttle" not in rate_limiting:
            rate_limiting["throttle"] = {}
        rate_limiting["throttle"].update(data.throttle)

    if data.runaway_detection is not None:
        if "runaway_detection" not in rate_limiting:
            rate_limiting["runaway_detection"] = {}
        rate_limiting["runaway_detection"].update(data.runaway_detection)

    # Save config
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
    except IOError as e:
        return {"error": f"Failed to save config: {e}"}

    # Invalidate cache
    get_rate_limiter().invalidate_config()

    return rate_limiting
