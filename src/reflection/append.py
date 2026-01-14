"""
Append Phase - Lightweight memory extraction after conversations.

This phase runs after each chat() call to extract noteworthy items
from the conversation into short-term memory.
"""

import json
from datetime import datetime
from typing import TYPE_CHECKING, List
import uuid

from ..llms import get_client
from ..tools.data.memory import _load_entries, _save_entries, VALID_TYPES

from .prompts import get_append_system_prompt, build_append_prompt

if TYPE_CHECKING:
    from .reflection import Reflection


def append_phase(reflection: "Reflection", user_message: str, assistant_response: str) -> int:
    """Run the append phase for a conversation.

    Calls LLM to extract noteworthy items and adds them to short-term memory.

    Args:
        reflection: The Reflection instance
        user_message: The user's message
        assistant_response: The assistant's response

    Returns:
        Number of items added to memory
    """
    agent_id = reflection.agent.id

    reflection.logger.info({
        "event": "append_start",
        "agent_id": agent_id
    })

    # Load current short-term memory for context
    existing_memory = _load_entries(agent_id)

    # Build prompt
    prompt = build_append_prompt(
        agent_profile=reflection.agent.profile,
        existing_memory=existing_memory,
        user_message=user_message,
        assistant_response=assistant_response
    )

    # Call LLM
    client = get_client()
    response = client.create(
        max_tokens=500,  # Keep it lightweight
        system=get_append_system_prompt(),
        messages=[{"role": "user", "content": prompt}],
        agent_id=f"{agent_id}/reflection"
    )

    # Extract text response
    text_response = ""
    for block in response.content:
        if hasattr(block, "text"):
            text_response += block.text

    # Parse JSON response
    new_items = _parse_items(text_response)

    reflection.logger.info({
        "event": "append_llm_response",
        "agent_id": agent_id,
        "items_extracted": len(new_items),
        "usage": {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens
        }
    })

    # Add valid items to short-term memory
    items_added = 0
    if new_items:
        items_added = _add_items_to_memory(new_items, existing_memory, agent_id)

    reflection.logger.info({
        "event": "append_complete",
        "agent_id": agent_id,
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

    return len(added)
