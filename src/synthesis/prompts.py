"""
Synthesis Prompts - LLM prompts for append and consolidate phases.

These prompts guide the LLM in extracting noteworthy items and synthesizing
patterns from memory into profiles.
"""

# =============================================================================
# Append Phase Prompts
# =============================================================================

APPEND_SYSTEM_PROMPT = """You are a memory extraction assistant. Your job is to identify noteworthy items from conversations that should be tracked in short-term memory.

Only extract genuinely new and important information. Be selective - not everything needs to be remembered.

Memory types:
- person: Someone to follow up with, check on, or reconnect with
- place: A location relevant to upcoming plans
- thing: Physical items, purchases, or objects of interest
- goal: Fitness goals, habits, skills being developed
- concern: Health issues, relationship tensions, work challenges
- idea: Projects to explore, insights, books, social media threads

Return a JSON array of items to remember. Each item must have:
- type: One of the types above
- short_description: Brief description (1-2 sentences)
- date_expected: Optional date (YYYY-MM-DD) when this becomes relevant, or null

Return an empty array [] if nothing is noteworthy."""


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

    return f"""## Agent Profile
{agent_profile}

## Currently Tracking (avoid duplicates)
{memory_text}

## Conversation to Analyze

**User:** {user_message}

**Assistant:** {assistant_response}

---

Extract any new noteworthy items from this conversation. Return JSON array only."""


# =============================================================================
# Consolidate Phase Prompts
# =============================================================================

CONSOLIDATE_SYSTEM_PROMPT_USER = """You are a profile synthesizer for a personal intelligence system. Your job is to analyze an agent's memories and update their profile based on observed behavioral patterns.

The profile captures who someone is based on their behavior - not what they say about themselves, but what their actions reveal.

## Cognitive Core Framework

1. Humans act to pursue what they desire and avoid what they fear
2. Strategies that reliably work are exploited and become stable patterns
3. Identity is the pattern of these attractors over time
4. The self-model (what people say about themselves) is often incomplete

## User Profile Schema

When updating a user profile, focus on:
1. **Biographical Information** - Name, contacts, factual details
2. **Wants and Fears** - Patterns revealing desires and fears (from behavior, not statements)
3. **Stable Attractors** - Recurring patterns the person returns to, especially under stress
4. **Notable Events and Actions** - Consistent or surprising moments
5. **Influences** - People, places, media, experiences that shape them
6. **Interests** - Goals, projects, work, hobbies

Return a JSON object with:
- long_term_entry: Summary of significant observations for permanent record (string or null)
- profile_updates: Specific changes to make to the profile (string describing updates, or null)
- graduate_ids: Array of short-term memory IDs that should be preserved in long-term"""


CONSOLIDATE_SYSTEM_PROMPT_AGENT = """You are a profile synthesizer for AI agents. Your job is to analyze an agent's activity and update their profile to better serve the user.

## AI Agent Profile Schema

When updating an AI agent profile, focus on:
1. **Purpose** - What the agent does and why
2. **Behavioral Rules** - Must/must not constraints learned from experience
3. **Voice** - Communication style and personality
4. **How I Work** - Specific workflows and patterns

Return a JSON object with:
- long_term_entry: Summary of significant activity for permanent record (string or null)
- profile_updates: Specific changes to make to the profile (string describing updates, or null)
- graduate_ids: Array of short-term memory IDs that should be preserved in long-term"""


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

    return f"""## {profile_type} Profile: {agent_id}

{agent_profile}

## Short-term Memory (last 90 days)

{short_term_text}

## Recent Long-term Memory

{long_term_text}

---

Analyze the patterns and provide your synthesis. Return JSON only."""


def get_consolidate_system_prompt(is_user: bool) -> str:
    """Get the appropriate system prompt for consolidation.

    Args:
        is_user: Whether this is the user agent

    Returns:
        System prompt string
    """
    return CONSOLIDATE_SYSTEM_PROMPT_USER if is_user else CONSOLIDATE_SYSTEM_PROMPT_AGENT
