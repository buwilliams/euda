"""
Profile Contract implementation for Euno.

This module provides:
- Profile validation (structure only, not content)
- Public profile generation via LLM
- CLI interface for profile operations

Design principles:
- Markdown-first, schema-light
- LLMs handle judgment, Python handles structure
- Artifact-class boundaries enforced in code
"""

from .validate import validate_profile, ValidationResult
from .generate import generate_public_profile

__all__ = [
    "validate_profile",
    "generate_public_profile",
    "ValidationResult",
]
