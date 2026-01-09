"""
Synthesis Module - Memory and profile management for agents.

Synthesis handles two phases for each agent:
1. Append (lightweight): After each chat, extract noteworthy items to short-term memory
2. Consolidate (heavy): On daily trigger, graduate memories and update profiles

This replaces the deprecated Profiler, Archivist, and Adaptor agents.
"""

from .synthesis import Synthesis

__all__ = ["Synthesis"]
