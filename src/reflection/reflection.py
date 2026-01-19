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
        # Inherit event sink from agent for dev CLI streaming
        self._event_sink = getattr(agent, "_event_sink", None)

    def _emit_to_sink(self, event: str, details: Optional[dict] = None):
        """Emit event to sink if configured (for dev CLI streaming)."""
        if self._event_sink:
            self._event_sink(event, {
                "agent_id": self.agent.id,
                **(details or {})
            })

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
        return AGENTS_DIR / self.agent.id / "identity.md"

    def _get_historical_profile_path(self, year: str) -> Path:
        """Get path to agent's historical profile for a specific year."""
        return AGENTS_DIR / self.agent.id / f"profile.{year}.md"

    def append(self, user_message: str, assistant_response: str, execution_id: str = None):
        """Append phase: Extract noteworthy items from a conversation.

        This is a lightweight operation called after each chat. Uses a quick
        LLM call to identify any new items worth tracking in short-term memory.

        Args:
            user_message: The user's message
            assistant_response: The assistant's response
            execution_id: Optional execution ID for SSE progress tracking
        """
        from .append import append_phase

        self._emit_to_sink("append_start", {"execution_id": execution_id})

        try:
            items_added = append_phase(self, user_message, assistant_response, execution_id)
            self._emit_to_sink("append_complete", {"items_added": items_added or 0, "execution_id": execution_id})
        except Exception as e:
            # Log error but don't block - append should not disrupt chat flow
            self.logger.error({
                "event": "append_error",
                "agent_id": self.agent.id,
                "execution_id": execution_id,
                "error": str(e)
            })
            self._emit_to_sink("append_error", {"error": str(e), "execution_id": execution_id})

    def consolidate(self, execution_id: str = None):
        """Consolidate phase: Graduate memories and update profile.

        This is a heavy operation run on daily trigger. Analyzes patterns
        in short-term and long-term memory to:
        1. Graduate important short-term items to long-term memory
        2. Update the agent's profile based on observed patterns
        3. Create historical profile snapshot at year boundaries

        Args:
            execution_id: Optional execution ID for SSE progress tracking
        """
        from .consolidate import consolidate_phase

        self._emit_to_sink("consolidate_start", {"execution_id": execution_id})

        try:
            result = consolidate_phase(self, execution_id)
            self._emit_to_sink("consolidate_complete", {
                "items_graduated": result.get("items_graduated", 0) if result else 0,
                "profile_updated": result.get("profile_updated", False) if result else False,
                "long_term_entry": result.get("long_term_entry", False) if result else False,
                "execution_id": execution_id,
            })
        except Exception as e:
            self.logger.error({
                "event": "consolidate_error",
                "agent_id": self.agent.id,
                "execution_id": execution_id,
                "error": str(e)
            })
            self._emit_to_sink("consolidate_error", {"error": str(e), "execution_id": execution_id})
            raise  # Re-raise for manager to handle retries

    def append_batch(self, exchanges: list, execution_id: str = None) -> int:
        """Batch append phase: Extract noteworthy items from multiple exchanges.

        This is an efficiency optimization for work cycles. Instead of calling
        append() after each iteration, we collect all exchanges and process
        them in a single LLM call at the end.

        Args:
            exchanges: List of (user_message, assistant_response) tuples
            execution_id: Optional execution ID for SSE progress tracking

        Returns:
            Total number of items added to memory
        """
        from .append import append_batch_phase

        if not exchanges:
            return 0

        self._emit_to_sink("append_batch_start", {
            "execution_id": execution_id,
            "exchange_count": len(exchanges)
        })

        try:
            items_added = append_batch_phase(self, exchanges, execution_id)
            self._emit_to_sink("append_batch_complete", {
                "items_added": items_added or 0,
                "exchange_count": len(exchanges),
                "execution_id": execution_id
            })
            return items_added or 0
        except Exception as e:
            # Log error but don't block
            self.logger.error({
                "event": "append_batch_error",
                "agent_id": self.agent.id,
                "execution_id": execution_id,
                "exchange_count": len(exchanges),
                "error": str(e)
            })
            self._emit_to_sink("append_batch_error", {"error": str(e), "execution_id": execution_id})
            return 0
