"""
Consolidation Module - Self-improvement capability for agents.

This module handles memory and identity consolidation:
- Append phase: Extract noteworthy items from conversations to short-term memory
- Consolidate phase: Graduate memories and update identities based on patterns

This is the self-improvement aspect of metacognition (formerly known as Reflection).
"""

from .consolidation import Consolidation

__all__ = ["Consolidation"]
