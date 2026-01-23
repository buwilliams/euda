"""
Memory Module - Conversation and long-term memory management.

Memory is the agent's ability to remember:
- Short-term: Session-based conversation history
- Long-term: Persistent archive accessed via RLM
"""

from .conversation import (
    ConversationManager,
    append_to_long_term_memory,
)
from .long_term import (
    LongTermMemory,
    load_memory,
    query_memory,
    get_long_term_dir,
)

__all__ = [
    # Conversation memory
    "ConversationManager",
    "append_to_long_term_memory",
    # Long-term memory
    "LongTermMemory",
    "load_memory",
    "query_memory",
    "get_long_term_dir",
]
