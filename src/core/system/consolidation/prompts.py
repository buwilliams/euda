"""
Consolidation Prompts - LLM prompts for append and consolidate phases.

Prompts are loaded from agent-level prompt directories (data/agents/{agent_id}/prompts/).
"""

from typing import Optional

from src.agent.cognition.reasoning.prompts import load_template, render_template


# =============================================================================
# Append Phase Prompts
# =============================================================================

def get_append_system_prompt(agent_id: Optional[str] = None) -> str:
    """Get the system prompt for the append phase."""
    return load_template("consolidation/append_system", agent_id=agent_id)


def build_append_prompt(
    agent_identity: str,
    existing_memory: list,
    user_message: str,
    assistant_response: str,
    agent_id: Optional[str] = None
) -> str:
    """Build the user prompt for the append phase.

    Args:
        agent_identity: The agent's current identity
        existing_memory: Current short-term memory items
        user_message: The user's message from the conversation
        assistant_response: The assistant's response
        agent_id: Optional agent ID for agent-specific prompt overrides

    Returns:
        Formatted prompt string
    """
    # Format existing memory for context
    if existing_memory:
        memory_lines = []
        for item in existing_memory:
            memory_lines.append(f"- [{item.get('type')}] {item.get('short_description')}")
        memory_text = "\n".join(memory_lines)
    else:
        memory_text = "(empty)"

    return render_template(
        "consolidation/append_user",
        agent_id=agent_id,
        agent_identity=agent_identity,
        existing_memory=memory_text,
        user_message=user_message,
        assistant_response=assistant_response
    )


def build_append_batch_prompt(
    agent_identity: str,
    existing_memory: list,
    exchanges: list,
    agent_id: Optional[str] = None
) -> str:
    """Build the user prompt for batched append phase.

    Args:
        agent_identity: The agent's current identity
        existing_memory: Current short-term memory items
        exchanges: List of (user_message, assistant_response) tuples
        agent_id: Optional agent ID for agent-specific prompt overrides

    Returns:
        Formatted prompt string
    """
    # Format existing memory for context
    if existing_memory:
        memory_lines = []
        for item in existing_memory:
            memory_lines.append(f"- [{item.get('type')}] {item.get('short_description')}")
        memory_text = "\n".join(memory_lines)
    else:
        memory_text = "(empty)"

    # Format all exchanges
    exchange_lines = []
    for i, (user_msg, assistant_msg) in enumerate(exchanges, 1):
        exchange_lines.append(f"### Exchange {i}")
        exchange_lines.append(f"**User:** {user_msg}")
        exchange_lines.append(f"**Assistant:** {assistant_msg}")
        exchange_lines.append("")

    exchanges_text = "\n".join(exchange_lines)

    return render_template(
        "consolidation/append_batch_user",
        agent_id=agent_id,
        agent_identity=agent_identity,
        existing_memory=memory_text,
        exchanges=exchanges_text,
        exchange_count=len(exchanges)
    )


# =============================================================================
# Consolidate Phase Prompts
# =============================================================================

def get_consolidate_system_prompt(is_user: bool, agent_id: Optional[str] = None) -> str:
    """Get the appropriate system prompt for consolidation.

    Args:
        is_user: Whether this is the user agent
        agent_id: Optional agent ID for agent-specific prompt overrides

    Returns:
        System prompt string
    """
    template_name = "consolidation/consolidate_system_user" if is_user else "consolidation/consolidate_system_agent"
    return load_template(template_name, agent_id=agent_id)


def build_consolidate_prompt(
    agent_id: str,
    agent_identity: str,
    short_term_memory: list,
    recent_long_term: str,
    completed_topics: list = None,
    is_user: bool = False
) -> str:
    """Build the user prompt for the consolidate phase.

    Args:
        agent_id: The agent's ID
        agent_identity: The agent's current identity
        short_term_memory: All short-term memory items
        recent_long_term: Recent long-term memory content
        completed_topics: List of recently completed topics
        is_user: Whether this is the user agent (selects appropriate system prompt)

    Returns:
        Formatted prompt string
    """
    # Format short-term memory
    if short_term_memory:
        memory_lines = []
        for item in short_term_memory:
            date_info = f"mentioned {item.get('date_mentioned', 'unknown')}"
            if item.get('date_expected'):
                date_info += f", expected {item['date_expected']}"
            memory_lines.append(
                f"- [{item.get('id')}] [{item.get('type')}] {item.get('short_description')} ({date_info})"
            )
        short_term_text = "\n".join(memory_lines)
    else:
        short_term_text = "(empty)"

    # Format long-term memory
    long_term_text = recent_long_term if recent_long_term else "(no recent entries)"

    # Format completed topics
    if completed_topics:
        topics_lines = []
        for topic in completed_topics:
            completed_at = topic.get('completed_at', '')
            if completed_at:
                # Extract just the date part
                completed_date = completed_at[:10] if len(completed_at) >= 10 else completed_at
            else:
                completed_date = 'recently'
            topics_lines.append(f"- {topic.get('title', 'Untitled')} (completed {completed_date})")
        completed_topics_text = "\n".join(topics_lines)
    else:
        completed_topics_text = "(no recent completed topics)"

    identity_type = "User" if is_user else "AI Agent"

    return render_template(
        "consolidation/consolidate_user",
        agent_id=agent_id,
        agent_identity=agent_identity,
        identity_type=identity_type,
        short_term_memory=short_term_text,
        recent_long_term=long_term_text,
        completed_topics=completed_topics_text
    )
