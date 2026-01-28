"""
Skill Exceptions - Error types for the skill system.
"""


class SkillError(Exception):
    """Base exception for skill-related errors."""
    pass


class SkillNotFoundError(SkillError):
    """Raised when a requested skill doesn't exist."""
    pass


class SkillExecutionError(SkillError):
    """Raised when a skill command fails to execute."""
    pass


class SkillTimeoutError(SkillError):
    """Raised when a skill execution times out."""
    pass


class SkillValidationError(SkillError):
    """Raised when a skill fails validation."""
    pass
