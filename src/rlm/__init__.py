"""
RLM (Recursive Language Model) Module

Provides RLM-powered memory access for long-term memory exploration.
Based on the Recursive Language Models paper (arXiv:2512.24601v1).
"""

from .repl import REPLEnvironment, ExecutionResult
from .client import RLMClient, RLMResult, RLMConfig
from .memory_loader import load_long_term_memory, get_memory_summary

__all__ = [
    'REPLEnvironment',
    'ExecutionResult',
    'RLMClient',
    'RLMResult',
    'RLMConfig',
    'load_long_term_memory',
    'get_memory_summary',
]
