"""
Integration tests for planning with LLM mocks.

Tests the Planner class using MockLLMClient to verify:
- Plan generation with realistic responses
- Plan injection into prompts
- Error handling when LLM fails

Spec: docs/3_system.md - "when an agent begins work on a topic, it first creates a brief plan"
"""

import pytest
from unittest.mock import MagicMock, patch

from tests.fixtures.llm import MockLLMClient
from tests.fixtures.llm.mock_client import MockResponse


class TestPlannerWithMockLLM:
    """Test Planner with mocked LLM responses."""

    def _create_planner(self):
        """Create a Planner with a mock agent."""
        from src.agent.cognition.reasoning.planning import Planner

        mock_agent = MagicMock()
        mock_agent.id = "test-agent"
        mock_agent._get_tools.return_value = [
            {"name": "create_topic", "description": "Create a new topic"},
            {"name": "list_topics", "description": "List all topics"},
        ]
        mock_agent.metacognition.should_plan.return_value = True
        mock_agent._log = MagicMock()

        return Planner(mock_agent)

    def test_create_plan_returns_text(self):
        """create_plan returns plan text from LLM."""
        planner = self._create_planner()
        topic = {"id": "topic-1", "name": "Test topic", "description": "Do something"}

        mock = MockLLMClient.from_fixture("planning")

        with mock.patch():
            plan = planner.create_plan(topic)

        assert plan is not None
        assert "Plan" in plan or "plan" in plan.lower()
        assert len(plan) > 20

    def test_create_plan_uses_correct_agent_id(self):
        """create_plan uses agent_id/planning for cost tracking."""
        planner = self._create_planner()
        topic = {"id": "topic-1", "name": "Test topic"}

        mock = MockLLMClient.simple(text="Step 1: Do it")

        with mock.patch():
            planner.create_plan(topic)

        # Verify the call was made with correct agent_id
        assert len(mock.calls) == 1
        assert mock.calls[0].agent_id == "test-agent/planning"
        assert mock.calls[0].topic_id == "topic-1"

    def test_create_plan_includes_topic_details(self):
        """create_plan includes topic name and description in prompt."""
        planner = self._create_planner()
        topic = {
            "id": "topic-1",
            "name": "Important Task",
            "description": "Complete this carefully",
            "tags": ["priority:high"]
        }

        mock = MockLLMClient.simple(text="Plan here")

        with mock.patch():
            planner.create_plan(topic)

        # Check the user message includes topic details
        user_content = mock.calls[0].messages[0]["content"]
        assert "Important Task" in user_content
        assert "Complete this carefully" in user_content
        assert "priority:high" in user_content

    def test_create_plan_includes_available_tools(self):
        """create_plan includes available tools in prompt."""
        planner = self._create_planner()
        topic = {"id": "topic-1", "name": "Test"}

        mock = MockLLMClient.simple(text="Plan")

        with mock.patch():
            planner.create_plan(topic)

        user_content = mock.calls[0].messages[0]["content"]
        assert "create_topic" in user_content
        assert "list_topics" in user_content

    def test_inject_plan_prepends_to_prompt(self):
        """inject_plan adds plan section at the start of prompt."""
        planner = self._create_planner()
        plan = "1. First step\n2. Second step"
        original_prompt = "## Task\nDo something important."

        result = planner.inject_plan(original_prompt, plan)

        # Plan should appear before original content
        assert result.index("Your Approach") < result.index("## Task")
        assert "First step" in result
        assert "Second step" in result
        assert "Do something important" in result

    def test_create_plan_handles_llm_error(self):
        """create_plan returns None on LLM error."""
        planner = self._create_planner()
        topic = {"id": "topic-1", "name": "Test"}

        mock = MockLLMClient.simple()

        with mock.patch():
            # Make the mock raise an exception
            with patch.object(mock, 'create', side_effect=Exception("API error")):
                plan = planner.create_plan(topic)

        assert plan is None
        # Verify error was logged
        planner.agent._log.assert_called()

    def test_create_plan_logs_start_and_complete(self):
        """create_plan logs planning_start and planning_complete."""
        planner = self._create_planner()
        topic = {"id": "topic-1", "name": "Test"}

        mock = MockLLMClient.simple(text="Plan")

        with mock.patch():
            planner.create_plan(topic)

        # Check logs were created
        log_calls = planner.agent._log.call_args_list
        events = [call[0][0] for call in log_calls]
        assert "planning_start" in events
        assert "planning_complete" in events


class TestPlanningWithFixtures:
    """Test planning scenarios using pre-recorded fixtures."""

    def _create_planner(self):
        """Create a Planner with a mock agent."""
        from src.agent.cognition.reasoning.planning import Planner

        mock_agent = MagicMock()
        mock_agent.id = "test-agent"
        mock_agent._get_tools.return_value = [
            {"name": "web_search", "description": "Search the web"},
            {"name": "read_file", "description": "Read files"},
        ]
        mock_agent.metacognition.should_plan.return_value = True
        mock_agent._log = MagicMock()

        return Planner(mock_agent)

    def test_planning_fixture_returns_structured_plan(self):
        """Planning fixture returns properly structured plan."""
        planner = self._create_planner()
        topic = {"id": "topic-1", "name": "Research topic"}

        mock = MockLLMClient.from_fixture("planning")

        with mock.patch():
            plan = planner.create_plan(topic)

        # Verify plan has structure
        assert plan is not None
        # Should have numbered steps or bullet points
        assert any(marker in plan for marker in ["1.", "2.", "-", "*"])

    def test_planning_fixture_matches_agent_id(self):
        """Planning fixture correctly matches agent_id pattern."""
        planner = self._create_planner()
        topic = {"id": "topic-1", "name": "Test"}

        mock = MockLLMClient.from_fixture("planning")

        with mock.patch():
            planner.create_plan(topic)

        # Verify call was made
        assert len(mock.calls) == 1
        # Response should come from fixture, not default
        response_text = mock.calls[0].response.content[0].text
        assert "Plan" in response_text
