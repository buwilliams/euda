"""
Agent Module - Re-export from new location.

This module re-exports from src/agent/ for backward compatibility.
New code should import from src.agent directly.
"""

from .agent import Agent, DATA_DIR, AGENTS_DIR

__all__ = ["Agent", "DATA_DIR", "AGENTS_DIR"]
