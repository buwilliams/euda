"""
Interest Matching Module - Matches content against agent interests.

Interests come from two sources:
1. Memory entries with type="interest" - keywords/themes the agent is tracking
2. Active topics assigned to the agent - titles expand the interest surface

Matching is lightweight (keyword-based, no LLM) for use in real-time chat
and periodic watchers.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

# Lazy imports to avoid circular dependency
# These are imported inside functions that use them
# from ..tools.data.memory import list_memory
# from ..tools.data.topics import list_topics
# from ..tools.agents.agents import list_agents


@dataclass
class Observation:
    """An observation to surface to an agent."""
    agent_id: str
    source: str  # "chat", "calendar", "mastodon"
    content: str
    matched_keyword: str
    matched_topic_id: Optional[str] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


def get_observing_agents() -> list[dict]:
    """Get all agents with observation enabled.

    Returns:
        List of agent configs with observation.enabled=True
    """
    from ..tools.agents.agents import list_agents

    agents = []
    for agent in list_agents():
        obs_config = agent.get("observation", {})
        if obs_config.get("enabled", False):
            agents.append(agent)
    return agents


def get_agent_interests(agent_id: str) -> list[str]:
    """Get all interest keywords for an agent.

    Interests come from:
    1. Memory entries with type="interest"
    2. Active topic names (todo/working status)

    Args:
        agent_id: The agent to get interests for

    Returns:
        List of lowercase keywords to match against
    """
    from ..tools.data.memory import list_memory
    from ..tools.data.topics import list_topics

    keywords = []

    # Get interest-type memories
    try:
        memories = list_memory(agent_id)
        for mem in memories:
            if mem.get("type") == "interest":
                desc = mem.get("short_description", "")
                if desc:
                    keywords.append(desc.lower())
    except Exception:
        pass  # Agent may not have memory yet

    # Get active topic names
    try:
        active_topics = list_topics(assignee=agent_id, status="todo")
        active_topics.extend(list_topics(assignee=agent_id, status="working"))
        for topic in active_topics:
            name = topic.get("name", "")
            if name and not name.startswith("euno:"):  # Skip internal topics
                # Extract meaningful words from topic name
                words = extract_keywords(name)
                keywords.extend(words)
    except Exception:
        pass  # Topics may not exist yet

    return list(set(keywords))  # Dedupe


def extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from text.

    Filters out common stop words and short words.

    Args:
        text: Text to extract keywords from

    Returns:
        List of lowercase keywords
    """
    # Common stop words to filter out
    stop_words = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
        "be", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "must", "shall", "can", "need",
        "this", "that", "these", "those", "it", "its", "my", "your", "our",
        "their", "what", "which", "who", "whom", "when", "where", "why", "how"
    }

    # Split on non-word characters and filter
    words = re.split(r'\W+', text.lower())
    keywords = [
        w for w in words
        if len(w) >= 3 and w not in stop_words
    ]

    return keywords


def matches_interests(content: str, agent_id: str) -> Optional[str]:
    """Check if content matches any of an agent's interests.

    Args:
        content: The content to check (message, event title, post text)
        agent_id: The agent whose interests to check against

    Returns:
        The matched keyword if found, None otherwise
    """
    keywords = get_agent_interests(agent_id)
    if not keywords:
        return None

    content_lower = content.lower()

    for keyword in keywords:
        # Match whole words or phrases
        if keyword in content_lower:
            return keyword

    return None


def check_content_for_observations(
    content: str,
    source: str,
    excluded_agents: list[str] = None
) -> list[Observation]:
    """Check content against all observing agents' interests.

    Args:
        content: The content to check
        source: Where the content came from ("chat", "calendar", "mastodon")
        excluded_agents: Agent IDs to skip (e.g., the agent that generated the content)

    Returns:
        List of observations for agents whose interests matched
    """
    if excluded_agents is None:
        excluded_agents = []

    observations = []

    for agent in get_observing_agents():
        agent_id = agent["id"]

        # Skip excluded agents
        if agent_id in excluded_agents:
            continue

        # Check if this source is enabled for this agent
        obs_config = agent.get("observation", {})
        sources = obs_config.get("sources", ["chat", "calendar", "mastodon"])
        if source not in sources:
            continue

        # Check for match
        matched = matches_interests(content, agent_id)
        if matched:
            observations.append(Observation(
                agent_id=agent_id,
                source=source,
                content=content,
                matched_keyword=matched
            ))

    return observations


# Cache for interests to avoid repeated lookups
_interest_cache: dict[str, tuple[datetime, list[str]]] = {}
_CACHE_TTL_SECONDS = 60  # Rebuild cache every minute


def get_agent_interests_cached(agent_id: str) -> list[str]:
    """Get agent interests with caching.

    Cache is invalidated after CACHE_TTL_SECONDS.

    Args:
        agent_id: The agent to get interests for

    Returns:
        List of lowercase keywords
    """
    now = datetime.now()

    if agent_id in _interest_cache:
        cached_time, cached_interests = _interest_cache[agent_id]
        age = (now - cached_time).total_seconds()
        if age < _CACHE_TTL_SECONDS:
            return cached_interests

    interests = get_agent_interests(agent_id)
    _interest_cache[agent_id] = (now, interests)
    return interests


def invalidate_interest_cache(agent_id: str = None):
    """Invalidate the interest cache.

    Args:
        agent_id: Specific agent to invalidate, or None for all
    """
    if agent_id:
        _interest_cache.pop(agent_id, None)
    else:
        _interest_cache.clear()
