"""
Long-Term Memory - Persistent memory storage via RLM.

Long-term memory is:
- Year-based archive: data/agents/{id}/memory/long-term/{yyyy}/{yyyy-mm-dd}.md
- Accessed through RLM for intelligent retrieval
- Primary store for identity evolution

All long-term memory access should go through RLM for intelligent exploration.
"""

from pathlib import Path
from typing import Optional

from ..rlm import RLMClient, load_long_term_memory as rlm_load_memory


DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


def get_long_term_dir(agent_id: str, year: Optional[str] = None) -> Path:
    """Get path to agent's long-term memory directory.

    Args:
        agent_id: The agent's ID
        year: Specific year (YYYY) or None for current year

    Returns:
        Path to long-term memory directory
    """
    from datetime import datetime
    year = year or datetime.now().strftime("%Y")
    return AGENTS_DIR / agent_id / "memory" / "long-term" / year


def load_memory(agent_id: str, days: int = 30) -> dict:
    """Load long-term memory for an agent via RLM.

    Args:
        agent_id: The agent's ID
        days: Number of days to look back

    Returns:
        Memory dict with entries and metadata
    """
    return rlm_load_memory(agent_id=agent_id, days=days)


def query_memory(agent_id: str, query: str, days: int = 30) -> dict:
    """Query long-term memory using RLM.

    Args:
        agent_id: The agent's ID
        query: Natural language query
        days: Number of days to look back

    Returns:
        RLM result with findings and sources
    """
    memory = rlm_load_memory(agent_id=agent_id, days=days)
    rlm = RLMClient(agent_id=agent_id)
    return rlm.query(query, memory)


class LongTermMemory:
    """Manages long-term memory access for an agent.

    Provides a class-based interface for memory operations.
    All access goes through RLM for intelligent retrieval.
    """

    def __init__(self, agent_id: str):
        """Initialize long-term memory manager.

        Args:
            agent_id: The agent's ID
        """
        self.agent_id = agent_id
        self._rlm = RLMClient(agent_id=agent_id)

    def load(self, days: int = 30) -> dict:
        """Load memory for the specified period.

        Args:
            days: Number of days to look back

        Returns:
            Memory dict with entries and metadata
        """
        return load_memory(self.agent_id, days)

    def query(self, query: str, days: int = 30) -> dict:
        """Query memory using natural language.

        Args:
            query: Natural language query
            days: Number of days to look back

        Returns:
            RLM result with findings and sources
        """
        memory = self.load(days)
        return self._rlm.query(query, memory)

    def extract_identity(self, current_profile: str, days: int = 30) -> dict:
        """Extract identity updates from memory.

        Args:
            current_profile: Current identity content
            days: Number of days to analyze

        Returns:
            RLM result with identity update suggestions
        """
        memory = self.load(days)
        return self._rlm.extract_identity(memory, current_profile)

    def discover_patterns(self, pattern_types: list, days: int = 30) -> dict:
        """Discover patterns in memory.

        Args:
            pattern_types: Types of patterns to discover
            days: Number of days to analyze

        Returns:
            Dict of discovered patterns by type
        """
        memory = self.load(days)
        return self._rlm.discover_patterns(memory, pattern_types)
