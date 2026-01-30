"""
Topics API Routes
"""

import re
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.data.topics import (
    list_topics, get_topic, create_topic, update_topic,
    complete_topic, restore_topic, archive_topic, add_topic_log, get_child_topics, delete_topic,
    assign_agent, unassign_agent, get_assignee, handoff_topic, unblock_topic
)
from src.core.data.assets import list_assets, read_asset, write_asset, delete_asset


router = APIRouter()


class CreateTopicRequest(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    tags: Optional[List[str]] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    someday: bool = False


class UpdateTopicRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    someday: Optional[bool] = None


class AssignAgentRequest(BaseModel):
    agent_id: str


class AddLogRequest(BaseModel):
    action: str
    agent: str = "user"


class TopicFeedbackRequest(BaseModel):
    message: str


class WriteAssetRequest(BaseModel):
    content: str


@router.get("")
def api_list_topics(status: Optional[str] = None, parent_id: Optional[str] = None, assignee: Optional[str] = None):
    """List all topics with optional filters."""
    return list_topics(status=status, parent_id=parent_id, assignee=assignee)


@router.get("/{topic_id}")
def api_get_topic(topic_id: str):
    """Get a topic by ID."""
    topic = get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic


@router.post("")
def api_create_topic(request: CreateTopicRequest):
    """Create a new topic."""
    return create_topic(
        name=request.name,
        description=request.description,
        parent_id=request.parent_id,
        tags=request.tags,
        assignee=request.assignee,
        due_date=request.due_date,
        someday=request.someday
    )


@router.patch("/{topic_id}")
def api_update_topic(topic_id: str, request: UpdateTopicRequest):
    """Update a topic."""
    result = update_topic(
        topic_id=topic_id,
        name=request.name,
        description=request.description,
        status=request.status,
        tags=request.tags,
        assignee=request.assignee,
        due_date=request.due_date,
        someday=request.someday
    )
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{topic_id}/complete")
def api_complete_topic(topic_id: str):
    """Mark a topic as completed."""
    result = complete_topic(topic_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{topic_id}/archive")
def api_archive_topic(topic_id: str):
    """Archive a topic."""
    result = archive_topic(topic_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{topic_id}/restore")
def api_restore_topic(topic_id: str):
    """Restore a completed topic back to todo."""
    result = restore_topic(topic_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{topic_id}/unblock")
def api_unblock_topic(topic_id: str):
    """Remove blocking tags (waiting:*, blocked:*) from a topic.

    This puts the topic back in agents' work queues.
    """
    was_blocked = unblock_topic(topic_id)
    if was_blocked:
        return {"status": "unblocked", "topic_id": topic_id}
    return {"status": "not_blocked", "topic_id": topic_id}


@router.delete("/{topic_id}")
def api_delete_topic(topic_id: str, delete_children: bool = False):
    """Delete a topic permanently."""
    result = delete_topic(topic_id, delete_children=delete_children)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{topic_id}/log")
def api_add_log(topic_id: str, request: AddLogRequest):
    """Add a log entry to a topic."""
    result = add_topic_log(topic_id, request.action, request.agent)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{topic_id}/feedback")
def api_topic_feedback(topic_id: str, request: TopicFeedbackRequest):
    """Send feedback about a topic to the appropriate agent.

    Routes to:
    1. pending_from agent (if topic was handed off to user)
    2. First assignee (if topic is assigned to an agent)
    3. Chat agent (fallback for routing)
    """
    # User providing feedback means they're engaging - unblock if blocked
    unblock_topic(topic_id)
    topic = get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Determine target agent
    target_agent = None

    # First check pending_from (who handed it to us)
    if topic.get("pending_from") and topic["pending_from"] != "user":
        target_agent = topic["pending_from"]

    # Otherwise check current assignee
    if not target_agent and topic.get("assignee") and topic["assignee"] != "user":
        target_agent = topic["assignee"]

    # Fallback to user agent for routing
    if not target_agent:
        target_agent = "user"

    # Append feedback to topic description
    current_desc = topic.get("description") or ""
    new_desc = f"{current_desc}\n\n---\n**User Feedback:** {request.message}"
    update_topic(topic_id, description=new_desc)

    # Hand off to agent
    result = handoff_topic(topic_id, target_agent, f"User feedback: {request.message}", agent="user")

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"status": "sent", "to_agent": target_agent, "topic_id": topic_id}


@router.get("/{topic_id}/chat/history")
def api_topic_chat_history(topic_id: str):
    """Get topic chat history from the topic asset."""
    from src.core.data.assets import ASSETS_DIR
    assets_dir = ASSETS_DIR / topic_id

    asset_name = None
    if assets_dir.exists():
        chat_assets = [
            p for p in assets_dir.iterdir()
            if p.is_file() and p.name.startswith("topic-chat-") and p.name.endswith(".md")
        ]
        if chat_assets:
            chat_assets.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            asset_name = chat_assets[0].name

    if not asset_name:
        return {"topic_id": topic_id, "messages": [], "conversation_id": None}

    asset = read_asset(topic_id, asset_name)
    if not asset or not asset.get("content"):
        return {"topic_id": topic_id, "messages": [], "conversation_id": None}

    content = asset["content"]
    parts = re.split(r'^## (User|Assistant) \([^)]+\)\n\n', content, flags=re.MULTILINE)
    messages = []
    i = 1
    while i < len(parts) - 1:
        role = parts[i].lower()
        msg_content = parts[i + 1].strip()
        if msg_content:
            messages.append({"role": role, "content": msg_content})
        i += 2

    conversation_id = asset_name[len("topic-chat-"):-3]

    return {"topic_id": topic_id, "messages": messages, "conversation_id": conversation_id}


@router.get("/{topic_id}/children")
def api_get_children(topic_id: str):
    """Get child topics."""
    return get_child_topics(topic_id)


@router.get("/{topic_id}/api-calls")
def api_get_topic_api_calls(topic_id: str, days: int = 7):
    """Get API calls made for this topic.

    Args:
        topic_id: ID of the topic
        days: Number of days to look back (default 7)

    Returns:
        Dict with call count, total cost, and list of API calls
    """
    from ...agent.cognition.metacognition import get_calls_by_topic, get_topic_call_count

    summary = get_topic_call_count(topic_id, days)
    calls = get_calls_by_topic(topic_id, days)

    return {
        **summary,
        "calls": calls
    }


# Assignment endpoints

@router.get("/{topic_id}/assignee")
def api_get_assignee(topic_id: str):
    """Get the agent assigned to a topic."""
    result = get_assignee(topic_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{topic_id}/assign")
def api_assign_agent(topic_id: str, request: AssignAgentRequest):
    """Assign an agent to a topic."""
    result = assign_agent(topic_id, request.agent_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{topic_id}/unassign")
def api_unassign_agent(topic_id: str, request: AssignAgentRequest):
    """Remove an agent from a topic."""
    result = unassign_agent(topic_id, request.agent_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# Asset endpoints

@router.get("/{topic_id}/assets")
def api_list_assets(topic_id: str):
    """List assets for a topic."""
    return list_assets(topic_id)


@router.get("/{topic_id}/assets/{filename}")
def api_get_asset(topic_id: str, filename: str):
    """Get an asset."""
    result = read_asset(topic_id, filename)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{topic_id}/assets/{filename}")
def api_write_asset(topic_id: str, filename: str, request: WriteAssetRequest):
    """Write an asset."""
    # User editing an asset signals they're working on this topic - unblock it
    unblock_topic(topic_id)
    return write_asset(topic_id, filename, request.content)


@router.delete("/{topic_id}/assets/{filename}")
def api_delete_asset(topic_id: str, filename: str):
    """Delete an asset."""
    result = delete_asset(topic_id, filename)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# Topic execution trace endpoint
@router.get("/{topic_id}/trace")
def api_get_topic_trace(topic_id: str, days: int = 7):
    """Get execution trace for a topic.

    Combines:
    - Topic logs from database (actions taken)
    - API calls from cost tracker (LLM interactions)

    Returns a chronological timeline of events.
    """
    from ...agent.cognition.metacognition import get_calls_by_topic

    topic = get_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Get topic logs from database
    from src.core.data.topics import get_topic_logs
    topic_logs = get_topic_logs(topic_id)

    # Get API calls
    api_calls = get_calls_by_topic(topic_id, days)

    # Normalize entries into a common trace format
    entries = []

    # Add topic logs
    for log in topic_logs:
        entries.append({
            "timestamp": log.get("timestamp"),
            "event": "action",
            "agent": log.get("agent"),
            "details": {
                "action": log.get("action")
            }
        })

    # Add API calls (LLM interactions)
    for call in api_calls:
        entries.append({
            "timestamp": call.get("timestamp"),
            "event": "llm_call",
            "agent": call.get("agent"),
            "details": {
                "model": call.get("model"),
                "input_tokens": call.get("input_tokens"),
                "output_tokens": call.get("output_tokens"),
                "cost": call.get("cost")
            }
        })

    # Sort by timestamp (oldest first for timeline)
    entries.sort(key=lambda x: x.get("timestamp", ""))

    # Calculate summary stats
    total_cost = sum(e.get("details", {}).get("cost", 0) for e in entries if e.get("event") == "llm_call")
    llm_calls = sum(1 for e in entries if e.get("event") == "llm_call")
    actions = sum(1 for e in entries if e.get("event") == "action")

    return {
        "topic_id": topic_id,
        "topic_name": topic.get("name"),
        "summary": {
            "llm_calls": llm_calls,
            "actions": actions,
            "total_cost": round(total_cost, 4)
        },
        "entries": entries
    }
