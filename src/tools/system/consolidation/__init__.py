"""
Consolidation Module - Memory and identity consolidation for agents.

This module provides:
1. The Consolidation class for agent-level memory management (append after chat)
2. The euno_consolidate tool for scheduled consolidation topics (identity updates)

Each Agent has a Consolidation instance that handles:
- Append phase: Extract noteworthy items from conversations to short-term memory
- Consolidate phase: Graduate memories and update identities based on patterns
"""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Callable

from ... import tool
from ....agent.logger import get_logger

if TYPE_CHECKING:
    from ....agent.agent import Agent


DATA_DIR = Path(__file__).parent.parent.parent.parent.parent / "data"
AGENTS_DIR = DATA_DIR / "agents"


class Consolidation:
    """Memory and identity consolidation capability for agents.

    Provides two phases:
    - append(): Lightweight extraction after each conversation
    - consolidate(): Heavy analysis on daily trigger (now via euno:consolidate topics)

    Note: consolidate() is kept for backwards compatibility but the preferred
    approach is to use euno:consolidate topics which call the euno_consolidate tool.
    """

    def __init__(self, agent: "Agent"):
        """Initialize Consolidation for an agent.

        Args:
            agent: The Agent instance this Consolidation belongs to
        """
        self._agent = agent
        self.agent_id = agent.id
        self.logger = get_logger("system/logs/consolidation")
        # Inherit event sink from agent for dev CLI streaming
        self._event_sink = getattr(agent, "_event_sink", None)

    @property
    def agent(self) -> "Agent":
        """Get the agent this consolidation belongs to (backwards compatibility)."""
        return self._agent

    @property
    def identity(self) -> str:
        """Get the agent's current identity."""
        return self._agent.identity

    def _emit_to_sink(self, event: str, details: Optional[dict] = None):
        """Emit event to sink if configured (for dev CLI streaming)."""
        if self._event_sink:
            self._event_sink(event, {
                "agent_id": self.agent_id,
                **(details or {})
            })

    def _get_config(self) -> dict:
        """Get consolidation configuration from agent config."""
        return self._agent.config.get("consolidation", {})

    def _get_short_term_path(self) -> Path:
        """Get path to agent's short-term memory file."""
        return AGENTS_DIR / self.agent_id / "memory" / "short-term.jsonl"

    def _get_long_term_dir(self, year: Optional[str] = None) -> Path:
        """Get path to agent's long-term memory directory (year-based).

        Args:
            year: Specific year (YYYY) or None for current year
        """
        year = year or datetime.now().strftime("%Y")
        return AGENTS_DIR / self.agent_id / "memory" / "long-term" / year

    def _get_identity_path(self) -> Path:
        """Get path to agent's current identity."""
        return AGENTS_DIR / self.agent_id / "identity.md"

    def _get_historical_identity_path(self, year: str) -> Path:
        """Get path to agent's historical identity for a specific year."""
        return AGENTS_DIR / self.agent_id / f"identity.{year}.md"

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
                "agent_id": self.agent_id,
                "execution_id": execution_id,
                "error": str(e)
            })
            self._emit_to_sink("append_error", {"error": str(e), "execution_id": execution_id})

    def consolidate(self, execution_id: str = None):
        """Consolidate phase: Graduate memories and update identity.

        This is a heavy operation run on daily trigger. Analyzes long-term
        memory to update the agent's identity based on observed patterns.

        Note: The preferred approach is to use euno:consolidate topics instead
        of calling this method directly.

        Args:
            execution_id: Optional execution ID for SSE progress tracking
        """
        from .consolidate import consolidate_phase

        # Create a runner that's compatible with the consolidate_phase function
        runner = ConsolidationRunner(self.agent_id, execution_id)

        self._emit_to_sink("consolidate_start", {"execution_id": execution_id})

        try:
            result = consolidate_phase(runner, execution_id)
            self._emit_to_sink("consolidate_complete", {
                "items_graduated": result.get("items_graduated", 0) if result else 0,
                "identity_updated": result.get("identity_updated", False) if result else False,
                "long_term_entry": result.get("long_term_entry", False) if result else False,
                "execution_id": execution_id,
            })
        except Exception as e:
            self.logger.error({
                "event": "consolidate_error",
                "agent_id": self.agent_id,
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
                "agent_id": self.agent_id,
                "execution_id": execution_id,
                "exchange_count": len(exchanges),
                "error": str(e)
            })
            self._emit_to_sink("append_batch_error", {"error": str(e), "execution_id": execution_id})
            return 0


class ConsolidationRunner:
    """Runs consolidation phases for an agent without requiring full Agent instance.

    This is used by the euno_consolidate tool and also by the Consolidation class
    for the consolidate phase.
    """

    def __init__(self, agent_id: str, execution_id: str = None):
        self.agent_id = agent_id
        self.execution_id = execution_id
        self.logger = get_logger("system/logs/consolidation")

    def _get_short_term_path(self) -> Path:
        """Get path to agent's short-term memory file."""
        return AGENTS_DIR / self.agent_id / "memory" / "short-term.jsonl"

    def _get_long_term_dir(self, year: Optional[str] = None) -> Path:
        """Get path to agent's long-term memory directory (year-based)."""
        year = year or datetime.now().strftime("%Y")
        return AGENTS_DIR / self.agent_id / "memory" / "long-term" / year

    def _get_identity_path(self) -> Path:
        """Get path to agent's current identity."""
        return AGENTS_DIR / self.agent_id / "identity.md"

    def _get_historical_identity_path(self, year: str) -> Path:
        """Get path to agent's historical identity for a specific year."""
        return AGENTS_DIR / self.agent_id / f"identity.{year}.md"

    @property
    def identity(self) -> str:
        """Load the agent's identity."""
        identity_path = self._get_identity_path()
        if identity_path.exists():
            return identity_path.read_text()
        return ""

    def run_consolidate(self) -> dict:
        """Run the consolidate phase (heavy analysis, identity updates).

        Returns:
            Dict with identity_updated flag
        """
        from .consolidate import consolidate_phase
        return consolidate_phase(self, self.execution_id)


@tool(
    "euno_consolidate",
    "Run consolidation for an agent. Internal system tool for scheduled consolidation topics.",
    tool_type="system"
)
def euno_consolidate(agent_id: str, phase: str = "consolidate") -> dict:
    """Execute consolidation directly without LLM involvement.

    This tool is called by the system when processing euno:consolidate topics.
    It runs the consolidation logic that analyzes long-term memory and updates identity.

    Args:
        agent_id: The agent to run consolidation for
        phase: Phase to run - "consolidate" (default), "append", or "both"
               Note: append is typically run automatically after chat, so
               scheduled topics usually run "consolidate" only.

    Returns:
        Dict with status and result details
    """
    import uuid

    execution_id = str(uuid.uuid4())[:8]
    runner = ConsolidationRunner(agent_id, execution_id)

    result = {
        "status": "completed",
        "agent_id": agent_id,
        "phase": phase,
        "execution_id": execution_id,
    }

    try:
        if phase in ("consolidate", "both"):
            consolidate_result = runner.run_consolidate()
            result["identity_updated"] = consolidate_result.get("identity_updated", False)

        runner.logger.info({
            "event": "euno_consolidate_complete",
            "agent_id": agent_id,
            "phase": phase,
            "result": result
        })

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        runner.logger.error({
            "event": "euno_consolidate_error",
            "agent_id": agent_id,
            "phase": phase,
            "error": str(e)
        })

    return result


# Export the Consolidation class for agent use
__all__ = ["Consolidation", "ConsolidationRunner", "euno_consolidate"]
