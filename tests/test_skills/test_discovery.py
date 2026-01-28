"""
Skill Discovery Tests.

Tests for skill discovery, validation, and caching.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestSkillDiscovery:
    """Test skill discovery functionality."""

    def test_discover_skills_finds_valid_skills(self):
        """Should find all valid skills in the skills directory."""
        from src.skills import discover_skills

        skills = discover_skills()

        # Should find our built-in skills
        skill_names = [s.name for s in skills]
        assert "core" in skill_names
        assert "nextcloud" in skill_names
        assert "speech" in skill_names
        assert "mastodon" in skill_names

    def test_discover_skills_returns_skill_info(self):
        """Should return SkillInfo objects with correct attributes."""
        from src.skills import discover_skills, SkillInfo

        skills = discover_skills()

        for skill in skills:
            assert isinstance(skill, SkillInfo)
            assert skill.name
            assert skill.path.is_dir()

    def test_discover_skills_extracts_descriptions(self):
        """Should extract descriptions from skill docstrings."""
        from src.skills import discover_skills

        skills = discover_skills()
        core_skill = next(s for s in skills if s.name == "core")

        # Core skill should have a description from its docstring
        assert core_skill.description
        assert "Core" in core_skill.description or "Euno" in core_skill.description

    def test_discover_skills_skips_hidden_directories(self, tmp_path):
        """Should skip directories starting with . or _."""
        from src.skills.discovery import discover_skills, SKILLS_DIR, invalidate_cache

        # Create a mock skills directory
        mock_skills = tmp_path / "skills"
        mock_skills.mkdir()

        # Create valid skill
        valid_skill = mock_skills / "valid"
        valid_skill.mkdir()
        (valid_skill / "cli.py").write_text('"""Valid skill."""\ndef main(): pass')

        # Create hidden/private directories
        hidden = mock_skills / ".hidden"
        hidden.mkdir()
        (hidden / "cli.py").write_text('def main(): pass')

        private = mock_skills / "_private"
        private.mkdir()
        (private / "cli.py").write_text('def main(): pass')

        with patch('src.skills.discovery.SKILLS_DIR', mock_skills):
            invalidate_cache()
            skills = discover_skills()

        skill_names = [s.name for s in skills]
        assert "valid" in skill_names
        assert ".hidden" not in skill_names
        assert "_private" not in skill_names


class TestSkillValidation:
    """Test skill validation functionality."""

    def test_validate_skill_requires_cli_py(self, tmp_path):
        """Should return False if cli.py doesn't exist."""
        from src.skills.discovery import validate_skill, SKILLS_DIR

        # Create skill dir without cli.py
        skill_dir = tmp_path / "skills" / "no_cli"
        skill_dir.mkdir(parents=True)

        with patch('src.skills.discovery.SKILLS_DIR', tmp_path / "skills"):
            assert validate_skill("no_cli") is False

    def test_validate_skill_requires_main_function(self, tmp_path):
        """Should return False if main() function doesn't exist."""
        from src.skills.discovery import validate_skill, SKILLS_DIR

        # Create skill with cli.py but no main()
        skill_dir = tmp_path / "skills" / "no_main"
        skill_dir.mkdir(parents=True)
        (skill_dir / "cli.py").write_text('def other_function(): pass')

        with patch('src.skills.discovery.SKILLS_DIR', tmp_path / "skills"):
            assert validate_skill("no_main") is False

    def test_validate_skill_accepts_valid_skill(self, tmp_path):
        """Should return True for valid skill structure."""
        from src.skills.discovery import validate_skill

        # Create valid skill
        skill_dir = tmp_path / "skills" / "valid"
        skill_dir.mkdir(parents=True)
        (skill_dir / "cli.py").write_text('"""Skill."""\ndef main(): pass')

        with patch('src.skills.discovery.SKILLS_DIR', tmp_path / "skills"):
            assert validate_skill("valid") is True

    def test_validate_skill_returns_false_for_nonexistent(self):
        """Should return False for nonexistent skill."""
        from src.skills.discovery import validate_skill

        assert validate_skill("nonexistent_skill_xyz") is False


class TestGetSkillInfo:
    """Test getting info for specific skills."""

    def test_get_skill_info_returns_info(self):
        """Should return SkillInfo for valid skill."""
        from src.skills import get_skill_info, SkillInfo

        info = get_skill_info("core")

        assert isinstance(info, SkillInfo)
        assert info.name == "core"
        assert info.path.is_dir()

    def test_get_skill_info_raises_for_nonexistent(self):
        """Should raise SkillNotFoundError for nonexistent skill."""
        from src.skills import get_skill_info, SkillNotFoundError

        with pytest.raises(SkillNotFoundError):
            get_skill_info("nonexistent_skill_xyz")

    def test_get_skill_info_raises_for_invalid(self, tmp_path):
        """Should raise SkillValidationError for invalid skill."""
        from src.skills.discovery import get_skill_info, SKILLS_DIR
        from src.skills import SkillValidationError

        # Create invalid skill (no main function)
        skill_dir = tmp_path / "skills" / "invalid"
        skill_dir.mkdir(parents=True)
        (skill_dir / "cli.py").write_text('x = 1')

        with patch('src.skills.discovery.SKILLS_DIR', tmp_path / "skills"):
            with pytest.raises(SkillValidationError):
                get_skill_info("invalid")


class TestSkillCache:
    """Test skill discovery caching."""

    def test_invalidate_cache_clears_cache(self):
        """Should clear the skill cache."""
        from src.skills.discovery import discover_skills, invalidate_cache, _skill_cache

        # First call populates cache
        skills1 = discover_skills()

        # Invalidate
        invalidate_cache()

        # Import again to check cache is None
        from src.skills import discovery
        assert discovery._skill_cache is None

    def test_discover_skills_uses_cache(self):
        """Should return cached results on subsequent calls."""
        from src.skills.discovery import discover_skills, invalidate_cache

        invalidate_cache()

        # First call
        skills1 = discover_skills()

        # Second call should return same objects
        skills2 = discover_skills()

        assert skills1 is skills2
