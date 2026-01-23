"""
Unit tests for planning configuration.

Tests for src/agent/cognition/metacognition/metacognition.py planning logic
and src/agent/cognition/metacognition/regulation/config.py planning config.

Spec: docs/3_system.md - "when an agent begins work on a job, it first creates a brief plan"
"""

import pytest
from unittest.mock import MagicMock, patch


class TestPlanningConfig:
    """Test planning configuration defaults and loading."""

    def test_default_planning_enabled(self):
        """Planning is enabled by default per docs/3_system.md."""
        from src.agent.cognition.metacognition.regulation.config import DEFAULT_CONFIG

        planning_config = DEFAULT_CONFIG["planning"]

        assert planning_config.get("enabled") is True

    def test_default_excluded_for_empty(self):
        """excluded_for list is empty by default (all jobs get planning)."""
        from src.agent.cognition.metacognition.regulation.config import DEFAULT_CONFIG

        planning_config = DEFAULT_CONFIG["planning"]

        assert planning_config.get("excluded_for") == []

    def test_get_planning_config_returns_defaults(self):
        """get_planning_config returns defaults when no overrides."""
        from src.agent.cognition.metacognition.regulation.config import MetacognitionConfig

        config = MetacognitionConfig(agent_id=None)

        # Mock the config loading to return empty (use defaults)
        with patch.object(config, '_load_system_config', return_value={}):
            with patch.object(config, '_load_agent_overrides', return_value={}):
                planning = config.get_planning_config()

        assert planning["enabled"] is True
        assert planning["excluded_for"] == []


class TestShouldPlan:
    """Test should_plan decision logic in Metacognition."""

    def _create_metacognition(self):
        """Create a Metacognition instance with mocked agent."""
        from src.agent.cognition.metacognition.metacognition import Metacognition

        mock_agent = MagicMock()
        mock_agent.id = "test-agent"
        return Metacognition(mock_agent)

    def test_should_plan_returns_true_by_default(self):
        """should_plan returns True for regular jobs when planning enabled."""
        metacognition = self._create_metacognition()

        # Mock config to return defaults
        with patch.object(metacognition.config, 'get_planning_config', return_value={
            "enabled": True,
            "excluded_for": []
        }):
            job = {"id": "job-1", "name": "Regular task", "tags": []}
            result = metacognition.should_plan(job)

        assert result is True

    def test_should_plan_returns_false_when_disabled(self):
        """should_plan returns False when planning is disabled."""
        metacognition = self._create_metacognition()

        with patch.object(metacognition.config, 'get_planning_config', return_value={
            "enabled": False,
            "excluded_for": []
        }):
            job = {"id": "job-1", "name": "Regular task", "tags": []}
            result = metacognition.should_plan(job)

        assert result is False

    def test_should_plan_excludes_matching_tags(self):
        """should_plan returns False when job tag matches excluded_for."""
        metacognition = self._create_metacognition()

        with patch.object(metacognition.config, 'get_planning_config', return_value={
            "enabled": True,
            "excluded_for": ["trigger:quick", "system:cleanup"]
        }):
            # Job with excluded tag
            job = {"id": "job-1", "name": "Quick task", "tags": ["trigger:quick"]}
            result = metacognition.should_plan(job)

        assert result is False

    def test_should_plan_allows_non_matching_tags(self):
        """should_plan returns True when job tags don't match exclusions."""
        metacognition = self._create_metacognition()

        with patch.object(metacognition.config, 'get_planning_config', return_value={
            "enabled": True,
            "excluded_for": ["trigger:quick"]
        }):
            # Job with different tags
            job = {"id": "job-1", "name": "Normal task", "tags": ["priority:high", "context:work"]}
            result = metacognition.should_plan(job)

        assert result is True

    def test_should_plan_handles_empty_tags(self):
        """should_plan works correctly when job has no tags."""
        metacognition = self._create_metacognition()

        with patch.object(metacognition.config, 'get_planning_config', return_value={
            "enabled": True,
            "excluded_for": ["trigger:quick"]
        }):
            job = {"id": "job-1", "name": "Task without tags", "tags": []}
            result = metacognition.should_plan(job)

        assert result is True

    def test_should_plan_handles_missing_tags_key(self):
        """should_plan works correctly when job dict has no tags key."""
        metacognition = self._create_metacognition()

        with patch.object(metacognition.config, 'get_planning_config', return_value={
            "enabled": True,
            "excluded_for": ["trigger:quick"]
        }):
            job = {"id": "job-1", "name": "Minimal job"}  # No tags key
            result = metacognition.should_plan(job)

        assert result is True


class TestPlannerIntegration:
    """Test Planner class integration with should_plan."""

    def test_planner_delegates_to_metacognition(self):
        """Planner.should_plan delegates to metacognition.should_plan."""
        from src.agent.cognition.reasoning.planning import Planner

        # Create mock agent with mock metacognition
        mock_agent = MagicMock()
        mock_agent.metacognition.should_plan.return_value = True

        planner = Planner(mock_agent)
        job = {"id": "job-1", "name": "Test job", "tags": []}

        result = planner.should_plan(job)

        assert result is True
        mock_agent.metacognition.should_plan.assert_called_once_with(job)

    def test_planner_respects_metacognition_false(self):
        """Planner respects False from metacognition.should_plan."""
        from src.agent.cognition.reasoning.planning import Planner

        mock_agent = MagicMock()
        mock_agent.metacognition.should_plan.return_value = False

        planner = Planner(mock_agent)
        job = {"id": "job-1", "name": "Excluded job", "tags": ["trigger:quick"]}

        result = planner.should_plan(job)

        assert result is False


class TestPlanningConfigMerging:
    """Test that planning config merges correctly from system and agent."""

    def test_agent_can_disable_planning(self, tmp_path):
        """Agent-level config can disable planning."""
        from src.agent.cognition.metacognition.regulation.config import MetacognitionConfig
        import json

        # Create agent config directory
        agents_dir = tmp_path / "agents" / "test-agent"
        agents_dir.mkdir(parents=True)

        # Write agent config with planning disabled
        agent_config = {
            "metacognition": {
                "planning": {
                    "enabled": False
                }
            }
        }
        (agents_dir / "config.json").write_text(json.dumps(agent_config))

        # Patch the AGENTS_DIR
        with patch('src.agent.cognition.metacognition.regulation.config.AGENTS_DIR', tmp_path / "agents"):
            with patch('src.agent.cognition.metacognition.regulation.config.CONFIG_PATH', tmp_path / "system" / "config.json"):
                config = MetacognitionConfig(agent_id="test-agent")
                planning = config.get_planning_config()

        assert planning["enabled"] is False

    def test_agent_can_add_exclusions(self, tmp_path):
        """Agent-level config can add to excluded_for list."""
        from src.agent.cognition.metacognition.regulation.config import MetacognitionConfig
        import json

        agents_dir = tmp_path / "agents" / "test-agent"
        agents_dir.mkdir(parents=True)

        agent_config = {
            "metacognition": {
                "planning": {
                    "excluded_for": ["agent:specific:tag"]
                }
            }
        }
        (agents_dir / "config.json").write_text(json.dumps(agent_config))

        with patch('src.agent.cognition.metacognition.regulation.config.AGENTS_DIR', tmp_path / "agents"):
            with patch('src.agent.cognition.metacognition.regulation.config.CONFIG_PATH', tmp_path / "system" / "config.json"):
                config = MetacognitionConfig(agent_id="test-agent")
                planning = config.get_planning_config()

        assert "agent:specific:tag" in planning["excluded_for"]
