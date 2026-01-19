"""
Reflection Module - Memory and identity management for agents.

Reflection handles two phases for each agent:
1. Append (lightweight): After each chat, extract noteworthy items to short-term memory
2. Consolidate (heavy): On daily trigger, graduate memories and update identities

This replaces the deprecated Profiler, Archivist, and Adaptor agents.
"""

from .reflection import Reflection

__all__ = ["Reflection"]
