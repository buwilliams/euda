"""
Append Phase - Lightweight memory extraction after conversations.

This phase runs after each chat() call to extract noteworthy items
from the conversation into short-term memory.
"""

import json
from datetime import datetime
from typing import TYPE_CHECKING, List
import uuid

from .....llms import get_client
from .....web.events import emit_ui_event
from .....tools.data.memory import _load_entries, _save_entries, VALID_TYPES

from .prompts import get_append_system_prompt, build_append_prompt, build_append_batch_prompt

if TYPE_CHECKING:
    from .consolidation import Consolidation


def append_phase(consolidation: "Consolidation", user_message: str, assistant_response: str, execution_id: str = None) -> int:
    """Run the append phase for a conversation.

    Calls LLM to extract noteworthy items and adds them to short-term memory.

    Args:
        reflection: The Reflection instance
        user_message: The user's message
        assistant_response: The assistant's response
        execution_id: Optional execution ID for SSE progress tracking

    Returns:
        Number of items added to memory
    """
    agent_id = consolidation.agent.id

    def emit_progress(step: str, message: str):
        """Emit SSE progress event."""
        emit_ui_event("consolidation:progress", {
            "execution_id": execution_id,
            "agent_id": agent_id,
            "phase": "append",
            "step": step,
            "message": message
        })

    consolidation.logger.info({
        "event": "append_start",
        "agent_id": agent_id,
        "execution_id": execution_id
    })

    emit_progress("loading_data", "Loading memory...")

    # Load current short-term memory for context
    existing_memory = _load_entries(agent_id)

    emit_progress("building_prompt", "Analyzing conversation...")

    # Build prompt
    prompt = build_append_prompt(
        agent_identity=consolidation.agent.identity,
        existing_memory=existing_memory,
        user_message=user_message,
        assistant_response=assistant_response
    )

    emit_progress("calling_llm", "Extracting memories...")

    # Call LLM
    client = get_client()
    response = client.create(
        system=get_append_system_prompt(),
        messages=[{"role": "user", "content": prompt}],
        agent_id=f"{agent_id}/reflection"
    )

    # Extract text response
    text_response = ""
    for block in response.content:
        if hasattr(block, "text"):
            text_response += block.text

    # Emit LLM complete event
    emit_ui_event("consolidation:llm_complete", {
        "execution_id": execution_id,
        "agent_id": agent_id,
        "phase": "append",
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens
    })

    # Parse JSON response
    new_items = _parse_items(text_response)

    consolidation.logger.info({
        "event": "append_llm_response",
        "agent_id": agent_id,
        "execution_id": execution_id,
        "items_extracted": len(new_items),
        "usage": {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens
        }
    })

    emit_progress("saving_results", "Saving memories...")

    # Add valid items to short-term memory
    items_added = 0
    if new_items:
        items_added = _add_items_to_memory(new_items, existing_memory, agent_id)

    consolidation.logger.info({
        "event": "append_complete",
        "agent_id": agent_id,
        "execution_id": execution_id,
        "items_added": items_added
    })

    # Emit completion event
    emit_ui_event("consolidation:complete", {
        "execution_id": execution_id,
        "agent_id": agent_id,
        "phase": "append",
        "items_added": items_added
    })

    return items_added


def _parse_items(response: str) -> List[dict]:
    """Parse LLM response into list of memory items.

    Args:
        response: Raw LLM response text

    Returns:
        List of valid memory item dicts
    """
    # Try to extract JSON from response
    text = response.strip()

    # Handle markdown code blocks
    if text.startswith("```"):
        # Remove code block markers
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines)

    try:
        items = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON array in response
        start = text.find("[")
        end = text.rfind("]") + 1
        if start != -1 and end > start:
            try:
                items = json.loads(text[start:end])
            except json.JSONDecodeError:
                return []
        else:
            return []

    if not isinstance(items, list):
        return []

    # Validate and clean items
    valid_items = []
    for item in items:
        if not isinstance(item, dict):
            continue

        item_type = item.get("type", "").lower()
        if item_type not in VALID_TYPES:
            continue

        description = item.get("short_description", "")
        if not description:
            continue

        valid_item = {
            "type": item_type,
            "short_description": description[:500],  # Limit length
            "date_expected": item.get("date_expected")
        }

        # Validate date format if provided
        if valid_item["date_expected"]:
            try:
                datetime.strptime(valid_item["date_expected"], "%Y-%m-%d")
            except ValueError:
                valid_item["date_expected"] = None

        valid_items.append(valid_item)

    return valid_items


def _add_items_to_memory(new_items: List[dict], existing_memory: List[dict], agent_id: str) -> int:
    """Add new items to short-term memory, avoiding duplicates.

    Args:
        new_items: Items to add (validated)
        existing_memory: Current memory entries
        agent_id: Agent ID for saving

    Returns:
        Number of items actually added (after deduplication)
    """
    # Build set of existing descriptions for deduplication
    existing_descriptions = {
        e.get("short_description", "").lower()
        for e in existing_memory
    }

    today = datetime.now().strftime("%Y-%m-%d")
    added = []

    for item in new_items:
        # Skip if similar item already exists
        if item["short_description"].lower() in existing_descriptions:
            continue

        entry = {
            "id": f"mem-{uuid.uuid4().hex[:8]}",
            "date_mentioned": today,
            "date_expected": item.get("date_expected"),
            "type": item["type"],
            "short_description": item["short_description"]
        }
        existing_memory.append(entry)
        added.append(entry)

    if added:
        _save_entries(existing_memory, agent_id)

        # Cross-pollinate user-relevant items to user's memory
        # Chat conversations are about the user, so user's identity should learn from them
        if agent_id == "chat":
            _cross_pollinate_to_user(added, today)

    return len(added)


def _cross_pollinate_to_user(items: List[dict], today: str) -> int:
    """Copy user-relevant memory items from chat to user's short-term memory.

    This enables the user's identity to evolve based on conversations with chat.
    Only user-focused types are copied (not learning/behavior which are agent-specific).

    Args:
        items: Items that were added to chat's memory
        today: Today's date string

    Returns:
        Number of items added to user's memory
    """
    # Types that describe the user (not how the agent should behave)
    USER_RELEVANT_TYPES = {"person", "place", "goal", "concern", "idea"}

    user_items = [i for i in items if i.get("type") in USER_RELEVANT_TYPES]
    if not user_items:
        return 0

    # Load user's current memory
    user_memory = _load_entries("user")
    user_existing = {e.get("short_description", "").lower() for e in user_memory}

    added = 0
    for item in user_items:
        # Skip duplicates
        if item["short_description"].lower() in user_existing:
            continue

        # Create a new entry for user's memory (new ID, track source)
        user_entry = {
            "id": f"mem-{uuid.uuid4().hex[:8]}",
            "date_mentioned": today,
            "date_expected": item.get("date_expected"),
            "type": item["type"],
            "short_description": item["short_description"],
            "source": "chat"  # Track where this came from
        }
        user_memory.append(user_entry)
        user_existing.add(item["short_description"].lower())
        added += 1

    if added:
        _save_entries(user_memory, "user")

    return added


def append_batch_phase(consolidation: "Consolidation", exchanges: list, execution_id: str = None) -> int:
    """Run the append phase for multiple conversation exchanges (batched).

    This is an efficiency optimization that processes multiple exchanges in a
    single LLM call instead of one call per exchange.

    Args:
        reflection: The Reflection instance
        exchanges: List of (user_message, assistant_response) tuples
        execution_id: Optional execution ID for SSE progress tracking

    Returns:
        Number of items added to memory
    """
    if not exchanges:
        return 0

    agent_id = consolidation.agent.id

    def emit_progress(step: str, message: str):
        """Emit SSE progress event."""
        emit_ui_event("consolidation:progress", {
            "execution_id": execution_id,
            "agent_id": agent_id,
            "phase": "append_batch",
            "step": step,
            "message": message
        })

    consolidation.logger.info({
        "event": "append_batch_start",
        "agent_id": agent_id,
        "execution_id": execution_id,
        "exchange_count": len(exchanges)
    })

    emit_progress("loading_data", "Loading memory...")

    # Load current short-term memory for context
    existing_memory = _load_entries(agent_id)

    emit_progress("building_prompt", f"Analyzing {len(exchanges)} exchanges...")

    # Build batch prompt
    prompt = build_append_batch_prompt(
        agent_identity=consolidation.agent.identity,
        existing_memory=existing_memory,
        exchanges=exchanges
    )

    emit_progress("calling_llm", "Extracting memories from exchanges...")

    # Call LLM
    client = get_client()
    response = client.create(
        system=get_append_system_prompt(),
        messages=[{"role": "user", "content": prompt}],
        agent_id=f"{agent_id}/reflection"
    )

    # Extract text response
    text_response = ""
    for block in response.content:
        if hasattr(block, "text"):
            text_response += block.text

    # Emit LLM complete event
    emit_ui_event("consolidation:llm_complete", {
        "execution_id": execution_id,
        "agent_id": agent_id,
        "phase": "append_batch",
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens
    })

    # Parse JSON response
    new_items = _parse_items(text_response)

    consolidation.logger.info({
        "event": "append_batch_llm_response",
        "agent_id": agent_id,
        "execution_id": execution_id,
        "items_extracted": len(new_items),
        "exchange_count": len(exchanges),
        "usage": {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens
        }
    })

    emit_progress("saving_results", "Saving memories...")

    # Add valid items to short-term memory
    items_added = 0
    if new_items:
        items_added = _add_items_to_memory(new_items, existing_memory, agent_id)

    consolidation.logger.info({
        "event": "append_batch_complete",
        "agent_id": agent_id,
        "execution_id": execution_id,
        "items_added": items_added,
        "exchange_count": len(exchanges)
    })

    # Emit completion event
    emit_ui_event("consolidation:complete", {
        "execution_id": execution_id,
        "agent_id": agent_id,
        "phase": "append_batch",
        "items_added": items_added,
        "exchange_count": len(exchanges)
    })

    return items_added
