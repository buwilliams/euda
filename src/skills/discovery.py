"""
Skill Discovery - Scan and validate skills.

Skills are discovered by scanning the skills/ directory for subdirectories
that contain a cli.py file with a main() function.
"""

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .exceptions import SkillNotFoundError, SkillValidationError


SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"

# Cache for discovered skills
_skill_cache: Optional[List["SkillInfo"]] = None


@dataclass
class SkillInfo:
    """Information about a discovered skill."""
    name: str
    path: Path
    description: str = ""

    def __str__(self) -> str:
        return f"{self.name}: {self.description}" if self.description else self.name


def _extract_skill_description(cli_path: Path) -> str:
    """Extract description from a skill's cli.py docstring.

    Args:
        cli_path: Path to the cli.py file

    Returns:
        First line of docstring or empty string
    """
    try:
        content = cli_path.read_text()
        # Look for module docstring
        if content.startswith('"""'):
            end = content.find('"""', 3)
            if end != -1:
                docstring = content[3:end].strip()
                # Return first line only
                return docstring.split("\n")[0].strip()
        elif content.startswith("'''"):
            end = content.find("'''", 3)
            if end != -1:
                docstring = content[3:end].strip()
                return docstring.split("\n")[0].strip()
    except Exception:
        pass
    return ""


def validate_skill(name: str) -> bool:
    """Validate that a skill exists and has the required structure.

    A valid skill has:
    - A directory at skills/{name}/
    - A cli.py file in that directory
    - A main() function in cli.py

    Args:
        name: Skill name (directory name)

    Returns:
        True if valid, False otherwise
    """
    skill_dir = SKILLS_DIR / name
    cli_path = skill_dir / "cli.py"

    if not skill_dir.is_dir():
        return False

    if not cli_path.is_file():
        return False

    # Check for main() function
    try:
        content = cli_path.read_text()
        # Simple check - look for def main
        if "def main(" not in content:
            return False
    except Exception:
        return False

    return True


def discover_skills() -> List[SkillInfo]:
    """Scan the skills directory and return info about valid skills.

    Returns:
        List of SkillInfo for each valid skill found
    """
    global _skill_cache

    if _skill_cache is not None:
        return _skill_cache

    skills = []

    if not SKILLS_DIR.is_dir():
        return skills

    for item in sorted(SKILLS_DIR.iterdir()):
        if item.is_dir() and not item.name.startswith(("_", ".")):
            if validate_skill(item.name):
                cli_path = item / "cli.py"
                description = _extract_skill_description(cli_path)
                skills.append(SkillInfo(
                    name=item.name,
                    path=item,
                    description=description
                ))

    _skill_cache = skills
    return skills


def get_skill_info(name: str) -> SkillInfo:
    """Get information about a specific skill.

    Args:
        name: Skill name

    Returns:
        SkillInfo for the skill

    Raises:
        SkillNotFoundError: If skill doesn't exist
        SkillValidationError: If skill is invalid
    """
    skill_dir = SKILLS_DIR / name

    if not skill_dir.is_dir():
        raise SkillNotFoundError(f"Skill not found: {name}")

    if not validate_skill(name):
        raise SkillValidationError(f"Skill {name} is invalid (missing cli.py or main())")

    cli_path = skill_dir / "cli.py"
    description = _extract_skill_description(cli_path)

    return SkillInfo(name=name, path=skill_dir, description=description)


def invalidate_cache():
    """Clear the skill discovery cache.

    Call this after adding or removing skills to force rediscovery.
    """
    global _skill_cache
    _skill_cache = None


def get_skill_path(name: str) -> Path:
    """Get the path to a skill's directory.

    Args:
        name: Skill name

    Returns:
        Path to skill directory

    Raises:
        SkillNotFoundError: If skill doesn't exist
    """
    skill_dir = SKILLS_DIR / name
    if not skill_dir.is_dir():
        raise SkillNotFoundError(f"Skill not found: {name}")
    return skill_dir
