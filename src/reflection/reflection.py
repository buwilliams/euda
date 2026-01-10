"""
Reflection - Core class for memory and profile reflection.

Each Agent has a Reflection instance that handles:
1. Append phase: Extract noteworthy items from conversations to short-term memory
2. Consolidate phase: Graduate memories and update profiles based on patterns
"""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from ..logger import get_logger

if TYPE_CHECKING:
    from ..agent import Agent


DATA_DIR = Path(__file__).parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


class Reflection:
    """Memory and profile reflection capability for agents.

    Provides two phases:
    - append(): Lightweight extraction after each conversation
    - consolidate(): Heavy analysis on daily trigger
    """

    def __init__(self, agent: "Agent"):
        """Initialize Reflection for an agent.

        Args:
            agent: The Agent instance this Reflection belongs to
        """
        self.agent = agent
        self.logger = get_logger("system/logs/reflection")

    def _get_config(self) -> dict:
        """Get reflection configuration from agent config."""
        return self.agent.config.get("reflection", {})

    def _get_short_term_path(self) -> Path:
        """Get path to agent's short-term memory file."""
        return AGENTS_DIR / self.agent.id / "memory" / "short-term.jsonl"

    def _get_long_term_dir(self, year: Optional[str] = None) -> Path:
        """Get path to agent's long-term memory directory (year-based).

        Args:
            year: Specific year (YYYY) or None for current year
        """
        year = year or datetime.now().strftime("%Y")
        return AGENTS_DIR / self.agent.id / "memory" / "long-term" / year

    def _get_profile_path(self) -> Path:
        """Get path to agent's current profile."""
        return AGENTS_DIR / self.agent.id / "profile.md"

    def _get_historical_profile_path(self, year: str) -> Path:
        """Get path to agent's historical profile for a specific year."""
        return AGENTS_DIR / self.agent.id / f"profile.{year}.md"

    def append(self, user_message: str, assistant_response: str):
        """Append phase: Extract noteworthy items from a conversation.

        This is a lightweight operation called after each chat. Uses a quick
        LLM call to identify any new items worth tracking in short-term memory.

        Args:
            user_message: The user's message
            assistant_response: The assistant's response
        """
        from .append import append_phase

        try:
            append_phase(self, user_message, assistant_response)
        except Exception as e:
            # Log error but don't block - append should not disrupt chat flow
            self.logger.error({
                "event": "append_error",
                "agent_id": self.agent.id,
                "error": str(e)
            })

    def consolidate(self):
        """Consolidate phase: Graduate memories and update profile.

        This is a heavy operation run on daily trigger. Analyzes patterns
        in short-term and long-term memory to:
        1. Graduate important short-term items to long-term memory
        2. Update the agent's profile based on observed patterns
        3. Create historical profile snapshot at year boundaries
        """
        from .consolidate import consolidate_phase

        try:
            consolidate_phase(self)
        except Exception as e:
            self.logger.error({
                "event": "consolidate_error",
                "agent_id": self.agent.id,
                "error": str(e)
            })
            raise  # Re-raise for manager to handle retries
