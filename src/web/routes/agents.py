"""
Agents API Routes
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from src.core.agents.agents import (
    list_agents, get_agent,
    get_agent_identity, update_agent_identity,
    get_agent_config, update_agent_config
)
from src.core.agents.monitoring import get_agent_monitoring
from src.core.data.topics import get_topics_completed_by_agent, create_topic, get_agent_inbox_topic
from src.core.data.identity import get_identity, update_identity
from src.core.data.memory import (
    list_memory, add_memory, remove_memory, write_long_term_memory
)
from ...agent.rlm import read_memory_date, list_memory_dates
from src.logger import get_logger
from ...agent.cognition.metacognition import get_token_awareness, AgentState


router = APIRouter()


class UpdateIdentityRequest(BaseModel):
    content: str


class UpdateConfigRequest(BaseModel):
    name: Optional[str] = None
    tools: Optional[List[str]] = None
    triggers: Optional[List[str]] = None
    consolidation: Optional[Dict[str, Any]] = None  # {enabled, trigger}


class TriggerReflectionRequest(BaseModel):
    phase: Optional[str] = "both"  # "append", "consolidate", or "both"


class TriggerRequest(BaseModel):
    topic_name: str  # e.g., "euno:consolidate", "euno:quote"
    instructions: Optional[str] = None


class AddMemoryRequest(BaseModel):
    short_description: str
    type: str
    date_expected: Optional[str] = None


class UpdateStateRequest(BaseModel):
    state: str  # "enabled", "disabled", "paused"
    reason: Optional[str] = None  # Required for "paused"


class WriteLongTermMemoryRequest(BaseModel):
    content: str
    date: Optional[str] = None


@router.get("")
def api_list_agents():
    """List all agents."""
    return list_agents()


@router.get("/{agent_id}")
def api_get_agent(agent_id: str):
    """Get agent details."""
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


# Identity endpoints
@router.get("/{agent_id}/identity")
def api_get_identity(agent_id: str):
    """Get agent's identity markdown."""
    identity = get_agent_identity(agent_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="Agent or identity not found")
    return {"agent_id": agent_id, "identity": identity}


@router.patch("/{agent_id}/identity")
def api_update_identity(agent_id: str, request: UpdateIdentityRequest):
    """Update agent's identity markdown."""
    result = update_agent_identity(agent_id, request.content)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# Config endpoints
@router.get("/{agent_id}/config")
def api_get_config(agent_id: str):
    """Get agent's configuration."""
    config = get_agent_config(agent_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return config


@router.patch("/{agent_id}/config")
def api_update_config(agent_id: str, request: UpdateConfigRequest):
    """Update agent's configuration (partial update)."""
    current_config = get_agent_config(agent_id)
    if current_config is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Apply partial updates
    if request.name is not None:
        current_config["name"] = request.name
    if request.tools is not None:
        current_config["tools"] = request.tools
    if request.triggers is not None:
        current_config["triggers"] = request.triggers
    if request.consolidation is not None:
        # Merge consolidation settings
        if "consolidation" not in current_config:
            current_config["consolidation"] = {}
        current_config["consolidation"].update(request.consolidation)

    result = update_agent_config(agent_id, current_config)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# Agent state endpoints
@router.get("/{agent_id}/state")
def api_get_state(agent_id: str):
    """Get agent's current operational state.

    Returns the agent state (enabled, disabled, paused) and related information
    including token usage statistics and time until budget reset.
    """
    config = get_agent_config(agent_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    token_awareness = get_token_awareness()
    state = token_awareness.get_agent_state(agent_id)
    pause_info = token_awareness.get_pause_info(agent_id)
    usage = token_awareness.get_agent_usage(agent_id)
    reset_info = token_awareness.get_time_until_reset(agent_id)

    return {
        "agent_id": agent_id,
        "state": state.value,
        "pause_info": pause_info if pause_info.get("is_paused") else None,
        "token_usage": usage,
        "budget_reset": reset_info
    }


@router.patch("/{agent_id}/state")
def api_update_state(agent_id: str, request: UpdateStateRequest):
    """Update agent's operational state.

    Allows enabling, disabling, or manually pausing an agent.
    To resume a paused agent, set state to "enabled".
    """
    config = get_agent_config(agent_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Validate state
    try:
        new_state = AgentState(request.state)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state: {request.state}. Must be 'enabled', 'disabled', or 'paused'"
        )

    # Paused state requires a reason
    if new_state == AgentState.PAUSED and not request.reason:
        raise HTTPException(
            status_code=400,
            detail="Reason is required when setting state to 'paused'"
        )

    token_awareness = get_token_awareness()
    token_awareness.set_agent_state(agent_id, new_state, request.reason)

    return {
        "agent_id": agent_id,
        "state": new_state.value,
        "reason": request.reason,
        "message": f"Agent state changed to {new_state.value}"
    }


@router.post("/{agent_id}/reset-usage")
def api_reset_usage(agent_id: str):
    """Reset token usage for an agent to zero.

    This clears the current period's token usage, allowing the agent to
    continue working if it was paused due to budget limits.
    """
    config = get_agent_config(agent_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    token_awareness = get_token_awareness()
    token_awareness.reset_agent_usage(agent_id)

    # Return updated usage stats
    usage = token_awareness.get_agent_usage(agent_id)
    reset_info = token_awareness.get_time_until_reset(agent_id)

    return {
        "agent_id": agent_id,
        "message": "Token usage reset to zero",
        "token_usage": usage,
        "budget_reset": reset_info
    }


# Short-term memory endpoints
@router.get("/{agent_id}/memory/short-term")
def api_get_short_term_memory(agent_id: str):
    """List agent's short-term memory items."""
    return list_memory(agent_id)


@router.post("/{agent_id}/memory/short-term")
def api_add_short_term_memory(agent_id: str, request: AddMemoryRequest):
    """Add a short-term memory item."""
    return add_memory(request.short_description, request.type, request.date_expected, agent_id)


@router.get("/{agent_id}/memory/short-term/{entry_id}")
def api_get_short_term_memory_item(agent_id: str, entry_id: str):
    """Get a single short-term memory item."""
    items = list_memory(agent_id)
    for item in items:
        if item.get("id") == entry_id:
            return item
    return {"error": "Memory item not found"}


@router.delete("/{agent_id}/memory/short-term/{entry_id}")
def api_remove_short_term_memory(agent_id: str, entry_id: str):
    """Remove a short-term memory item."""
    return remove_memory(entry_id, agent_id)


# Long-term memory endpoints
@router.get("/{agent_id}/memory/long-term")
def api_get_long_term_memory(
    agent_id: str,
    date: Optional[str] = None,
    offset: int = 0,
    limit: Optional[int] = None
):
    """Get agent's long-term memory entries."""
    if date:
        return read_memory_date(agent_id, date, offset=offset, limit=limit)
    else:
        # Return empty result if no date specified
        return {"error": "date parameter required"}


@router.post("/{agent_id}/memory/long-term")
def api_write_long_term_memory(agent_id: str, request: WriteLongTermMemoryRequest):
    """Add a long-term memory entry."""
    return write_long_term_memory(request.content, request.date, agent_id)


@router.get("/{agent_id}/memory/long-term/dates")
def api_list_long_term_memory_dates(agent_id: str):
    """List all dates with long-term memory entries."""
    result = list_memory_dates(agent_id)
    # Return just the dates array for backward compatibility with UI
    return result["dates"]


# Completed topics by agent endpoint
@router.get("/{agent_id}/completed-topics")
def api_get_completed_topics(agent_id: str, limit: int = 20):
    """Get topics completed by this agent."""
    return get_topics_completed_by_agent(agent_id, limit)


# Monitoring endpoint
@router.get("/{agent_id}/monitoring")
def api_get_monitoring(agent_id: str, offset: int = 0, limit: int = 20):
    """Get LLM monitoring stats for this agent with pagination.

    Args:
        agent_id: The agent ID to query
        offset: Number of entries to skip (for pagination)
        limit: Maximum number of entries to return (default 20)
    """
    return get_agent_monitoring(agent_id, offset=offset, limit=limit)


# Reflection trigger endpoint
@router.post("/{agent_id}/reflection/trigger")
def api_trigger_reflection(agent_id: str, request: TriggerReflectionRequest = None):
    """Trigger reflection for an agent by creating a trigger topic.

    Creates a topic with tags=["trigger:consolidation:{phase}"] that the agent
    will pick up and process during its work cycle.

    Returns an execution_id for SSE progress tracking.
    """
    # Verify agent exists
    config = get_agent_config(agent_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    phase = request.phase if request else "both"
    if phase not in ("append", "consolidate", "both"):
        raise HTTPException(status_code=400, detail="phase must be 'append', 'consolidate', or 'both'")

    # Generate execution_id for SSE tracking
    execution_id = f"exec-{uuid.uuid4().hex[:8]}"

    today = datetime.now().strftime("%Y-%m-%d")
    inbox = get_agent_inbox_topic(agent_id)
    parent_id = inbox["id"] if inbox else None

    topic = create_topic(
        name="euno:consolidate",
        description=f"Manual consolidation trigger - phase: {phase} (execution_id: {execution_id})",
        parent_id=parent_id,
        assignee=agent_id,
        tags=["ui:manual", f"execution:{execution_id}"],
        created_by="web-ui"
    )

    return {
        "status": "triggered",
        "execution_id": execution_id,
        "agent_id": agent_id,
        "phase": phase,
        "topic_id": topic["id"],
        "timestamp": datetime.now().isoformat()
    }


# General trigger endpoint
@router.post("/{agent_id}/trigger")
def api_trigger(agent_id: str, request: TriggerRequest):
    """Trigger any scheduled event for an agent by creating a trigger topic.

    Creates a topic with the specified name that the agent will pick up
    and process during its work cycle.

    Args:
        agent_id: The agent to trigger
        request: Contains topic_name (required) and instructions (optional)

    Returns an execution_id for SSE progress tracking.
    """
    # Verify agent exists
    config = get_agent_config(agent_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Generate execution_id for SSE tracking
    execution_id = f"exec-{uuid.uuid4().hex[:8]}"

    inbox = get_agent_inbox_topic(agent_id)
    parent_id = inbox["id"] if inbox else None

    description = request.instructions or f"Manual trigger (execution_id: {execution_id})"

    topic = create_topic(
        name=request.topic_name,
        description=description,
        parent_id=parent_id,
        assignee=agent_id,
        tags=["ui:manual", f"execution:{execution_id}"],
        created_by="web-ui"
    )

    return {
        "status": "triggered",
        "execution_id": execution_id,
        "agent_id": agent_id,
        "topic_name": request.topic_name,
        "topic_id": topic["id"],
        "timestamp": datetime.now().isoformat()
    }


# Active executions endpoint
@router.get("/{agent_id}/active-executions")
def api_get_active_executions(agent_id: str):
    """Get active trigger topics for an agent to restore UI state after page refresh.

    Returns active trigger topics (consolidation) that are assigned to this agent
    and still in todo status. This allows the UI to restore the running state of buttons.

    Returns:
        List of active executions with execution_id, phase, topic_id, created_at
    """
    from src.core.data.topics import list_topics

    # Verify agent exists
    config = get_agent_config(agent_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get todo topics assigned to this agent
    topics = list_topics(status="todo", assignee=agent_id)

    # Filter for consolidation topics and extract execution info
    executions = []
    for topic in topics:
        topic_name = topic.get("name", "")
        tags = topic.get("tags", [])

        # Check for consolidation topic
        if topic_name != "euno:consolidate":
            continue

        # Extract phase from description if available
        description = topic.get("description", "")
        if "phase: append" in description:
            phase = "append"
        elif "phase: consolidate" in description:
            phase = "consolidate"
        else:
            phase = "both"

        # Extract execution_id from tags
        execution_id = None
        for tag in tags:
            if tag.startswith("execution:"):
                execution_id = tag.split(":", 1)[1]
                break

        executions.append({
            "execution_id": execution_id,
            "phase": phase,
            "topic_id": topic["id"],
            "created_at": topic.get("created_at")
        })

    return executions


# Consolidation logs endpoint
@router.get("/{agent_id}/logs/consolidation")
def api_get_consolidation_logs(agent_id: str, days: int = 7):
    """Get consolidation logs for this agent.

    Returns log entries from the last N days, filtered by agent_id.
    """
    # Verify agent exists
    config = get_agent_config(agent_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    logger = get_logger("system/logs/consolidation")
    all_logs = logger.read_logs(days=days)

    # Filter by agent_id
    agent_logs = [
        log for log in all_logs
        if log.get("agent_id") == agent_id
    ]

    # Sort by timestamp descending (most recent first)
    agent_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return {
        "agent_id": agent_id,
        "days": days,
        "logs": agent_logs
    }
