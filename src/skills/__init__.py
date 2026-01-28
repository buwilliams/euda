"""
Skill System - CLI-based skill architecture for Euno.

This module provides infrastructure for discovering, validating, and executing
skills that extend Euno's capabilities.

Skills are CLI applications in the skills/ directory. The LLM interacts with
them through three meta-tools: list_skills, skill_usage, and execute_skill.

Public API:
- discover_skills() - Find all valid skills
- get_skill_info(name) - Get info about a specific skill
- execute_skill(name, command) - Run a skill command
- get_skill_usage(name) - Get help text for a skill
- get_meta_tools() - Get tool definitions for LLM
- execute_meta_tool(name, inputs) - Execute a meta-tool
"""

from .discovery import (
    discover_skills,
    get_skill_info,
    validate_skill,
    invalidate_cache,
    SkillInfo,
)

from .executor import (
    execute_skill,
    SkillResult,
)

from .usage import (
    get_skill_usage,
    get_skill_commands,
    get_all_skills_summary,
)

from .tools import (
    get_meta_tools,
    execute_meta_tool,
    list_skills_tool,
    skill_usage_tool,
    execute_skill_tool,
)

from .context import (
    build_skill_env,
    get_data_dir_from_env,
    get_agent_id_from_env,
    get_topic_id_from_env,
    get_session_id_from_env,
)

from .exceptions import (
    SkillError,
    SkillNotFoundError,
    SkillExecutionError,
    SkillTimeoutError,
    SkillValidationError,
)

__all__ = [
    # Discovery
    "discover_skills",
    "get_skill_info",
    "validate_skill",
    "invalidate_cache",
    "SkillInfo",
    # Execution
    "execute_skill",
    "SkillResult",
    # Usage
    "get_skill_usage",
    "get_skill_commands",
    "get_all_skills_summary",
    # Tools
    "get_meta_tools",
    "execute_meta_tool",
    "list_skills_tool",
    "skill_usage_tool",
    "execute_skill_tool",
    # Context
    "build_skill_env",
    "get_data_dir_from_env",
    "get_agent_id_from_env",
    "get_topic_id_from_env",
    "get_session_id_from_env",
    # Exceptions
    "SkillError",
    "SkillNotFoundError",
    "SkillExecutionError",
    "SkillTimeoutError",
    "SkillValidationError",
]
