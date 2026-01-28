"""
Skill Tools - Meta-tools for LLM to interact with skills.

These three tools replace 82+ specialized tools with a skill-based approach.
The LLM uses these to discover, understand, and execute skill commands.
"""

from typing import List, Optional

from .discovery import discover_skills, get_skill_info
from .executor import execute_skill, SkillResult
from .usage import get_skill_usage, get_all_skills_summary
from .exceptions import SkillError, SkillNotFoundError


# Tool type for all meta-tools
TOOL_TYPE = "system"


def list_skills_tool(excluded_skills: Optional[List[str]] = None) -> dict:
    """List all available skills.

    Args:
        excluded_skills: List of skill names to exclude from results

    Returns:
        Dict with skills list and summary
    """
    skills = discover_skills()

    # Filter excluded skills
    if excluded_skills:
        skills = [s for s in skills if s.name not in excluded_skills]

    skill_list = []
    for skill in skills:
        skill_list.append({
            "name": skill.name,
            "description": skill.description or "(no description)"
        })

    return {
        "skills": skill_list,
        "count": len(skill_list),
        "hint": "Use skill_usage(name) to see commands for a skill"
    }


def skill_usage_tool(skill: str) -> dict:
    """Get CLI help for a skill.

    Args:
        skill: Skill name

    Returns:
        Dict with usage text or error
    """
    try:
        usage = get_skill_usage(skill)
        return {
            "skill": skill,
            "usage": usage
        }
    except SkillNotFoundError:
        return {"error": f"Skill not found: {skill}"}
    except SkillError as e:
        return {"error": str(e)}


def execute_skill_tool(
    skill: str,
    command: str,
    agent_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> dict:
    """Execute a skill command.

    Args:
        skill: Skill name
        command: Command string (e.g., "topics list --status todo")
        agent_id: Current agent ID (optional, for context)
        topic_id: Current topic ID (optional, for context)
        session_id: Current session ID (optional, for context)

    Returns:
        Dict with success status, output, and exit code
    """
    try:
        result = execute_skill(
            skill,
            command,
            timeout=60,
            agent_id=agent_id,
            topic_id=topic_id,
            session_id=session_id
        )

        return {
            "success": result.success,
            "output": result.output,
            "exit_code": result.exit_code
        }
    except SkillNotFoundError:
        return {"error": f"Skill not found: {skill}"}
    except SkillError as e:
        return {"error": str(e)}


def get_meta_tools() -> list:
    """Get the three meta-tool definitions for LLM use.

    Returns:
        List of tool definitions in Claude tool format
    """
    return [
        {
            "name": "list_skills",
            "description": "List all available skills. Use to discover what capabilities are available.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "skill_usage",
            "description": "Get CLI help for a skill. Shows available commands and their arguments. Use before executing an unfamiliar skill.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "skill": {
                        "type": "string",
                        "description": "Skill name (e.g., 'core', 'nextcloud')"
                    }
                },
                "required": ["skill"]
            }
        },
        {
            "name": "execute_skill",
            "description": "Execute a skill command. Run skill commands to perform actions like managing topics, memory, or external integrations.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "skill": {
                        "type": "string",
                        "description": "Skill name (e.g., 'core', 'nextcloud')"
                    },
                    "command": {
                        "type": "string",
                        "description": "Command string including subcommands and arguments (e.g., 'topics list --status todo')"
                    }
                },
                "required": ["skill", "command"]
            }
        }
    ]


def execute_meta_tool(name: str, inputs: dict, agent_context: dict = None) -> dict:
    """Execute a meta-tool by name.

    Args:
        name: Tool name (list_skills, skill_usage, execute_skill)
        inputs: Tool inputs
        agent_context: Optional context with agent_id, topic_id, session_id

    Returns:
        Tool result dict
    """
    context = agent_context or {}

    if name == "list_skills":
        excluded = context.get("excluded_skills", [])
        return list_skills_tool(excluded_skills=excluded)

    elif name == "skill_usage":
        return skill_usage_tool(inputs.get("skill", ""))

    elif name == "execute_skill":
        return execute_skill_tool(
            skill=inputs.get("skill", ""),
            command=inputs.get("command", ""),
            agent_id=context.get("agent_id"),
            topic_id=context.get("topic_id"),
            session_id=context.get("session_id")
        )

    else:
        return {"error": f"Unknown meta-tool: {name}"}
