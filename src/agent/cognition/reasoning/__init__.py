"""
Reasoning Module - First-order thinking for agents.

Provides:
- System prompt building
- Strategic planning for complex tasks
- LLM call execution and tool handling

This is the reasoning aspect of cognition (first-order thinking).
"""

from .planning import Planner

__all__ = ["Planner"]
