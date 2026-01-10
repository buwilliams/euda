"""
Reflection Prompts - LLM prompts for append and consolidate phases.

Prompts are loaded from data/system/prompts/ templates.
"""

from ..prompts import load_template, render_template


# =============================================================================
# Append Phase Prompts
# =============================================================================

def get_append_system_prompt() -> str:
    """Get the system prompt for the append phase."""
    return load_template("reflection/append_system")


def build_append_prompt(
    agent_profile: str,
    existing_memory: list,
    user_message: str,
    assistant_response: str
) -> str:
    """Build the user prompt for the append phase.

    Args:
        agent_profile: The agent's current profile
        existing_memory: Current short-term memory items
        user_message: The user's message from the conversation
        assistant_response: The assistant's response

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
        "reflection/append_user",
        agent_profile=agent_profile,
        existing_memory=memory_text,
        user_message=user_message,
        assistant_response=assistant_response
    )


# =============================================================================
# Consolidate Phase Prompts
# =============================================================================

def get_consolidate_system_prompt(is_user: bool) -> str:
    """Get the appropriate system prompt for consolidation.

    Args:
        is_user: Whether this is the user agent

    Returns:
        System prompt string
    """
    template_name = "reflection/consolidate_system_user" if is_user else "reflection/consolidate_system_agent"
    return load_template(template_name)


def build_consolidate_prompt(
    agent_id: str,
    agent_profile: str,
    short_term_memory: list,
    recent_long_term: str,
    is_user: bool
) -> str:
    """Build the user prompt for the consolidate phase.

    Args:
        agent_id: The agent's ID
        agent_profile: The agent's current profile
        short_term_memory: All short-term memory items
        recent_long_term: Recent long-term memory content
        is_user: Whether this is the user agent (uses different schema)

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

    profile_type = "User" if is_user else "AI Agent"

    return render_template(
        "reflection/consolidate_user",
        profile_type=profile_type,
        agent_id=agent_id,
        agent_profile=agent_profile,
        short_term_memory=short_term_text,
        recent_long_term=long_term_text
    )
