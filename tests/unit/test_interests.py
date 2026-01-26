"""
Unit tests for interest matching module.

Tests for src/agent/interests.py
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock


class TestExtractKeywords:
    """Test keyword extraction from text."""

    def test_extract_keywords_basic(self):
        """Extract keywords from simple text."""
        from src.agent.interests import extract_keywords

        keywords = extract_keywords("Learn about machine learning")

        assert "learn" in keywords
        assert "machine" in keywords
        assert "learning" in keywords

    def test_extract_keywords_filters_stop_words(self):
        """Stop words are filtered out."""
        from src.agent.interests import extract_keywords

        keywords = extract_keywords("The quick brown fox and the lazy dog")

        assert "the" not in keywords
        assert "and" not in keywords
        assert "quick" in keywords
        assert "brown" in keywords
        assert "lazy" in keywords

    def test_extract_keywords_filters_short_words(self):
        """Words shorter than 3 characters are filtered."""
        from src.agent.interests import extract_keywords

        keywords = extract_keywords("I am a go to AI")

        assert "am" not in keywords
        assert "go" not in keywords
        assert "ai" not in keywords  # Too short

    def test_extract_keywords_lowercase(self):
        """Keywords are lowercased."""
        from src.agent.interests import extract_keywords

        keywords = extract_keywords("PYTHON Programming")

        assert "python" in keywords
        assert "PYTHON" not in keywords
        assert "programming" in keywords

    def test_extract_keywords_empty_text(self):
        """Empty text returns empty list."""
        from src.agent.interests import extract_keywords

        keywords = extract_keywords("")

        assert keywords == []

    def test_extract_keywords_splits_on_punctuation(self):
        """Keywords are split on non-word characters (but not underscores)."""
        from src.agent.interests import extract_keywords

        keywords = extract_keywords("python-programming, data science!")

        assert "python" in keywords
        assert "programming" in keywords
        assert "data" in keywords
        assert "science" in keywords


class TestMatchesInterests:
    """Test interest matching function."""

    def test_matches_interests_found(self, patch_data_dir):
        """Returns matched keyword when found."""
        from src.agent.interests import matches_interests
        from src.tools.data.memory import add_memory

        # Create agent and add interest
        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        add_memory(
            short_description="python",
            type="interest",
            agent_id="test-agent"
        )

        result = matches_interests("I love programming in Python", "test-agent")

        assert result == "python"

    def test_matches_interests_not_found(self, patch_data_dir):
        """Returns None when no match."""
        from src.agent.interests import matches_interests
        from src.tools.data.memory import add_memory

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        add_memory(
            short_description="python",
            type="interest",
            agent_id="test-agent"
        )

        result = matches_interests("I love programming in JavaScript", "test-agent")

        assert result is None

    def test_matches_interests_case_insensitive(self, patch_data_dir):
        """Matching is case insensitive."""
        from src.agent.interests import matches_interests
        from src.tools.data.memory import add_memory

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        add_memory(
            short_description="PYTHON",
            type="interest",
            agent_id="test-agent"
        )

        result = matches_interests("learning python today", "test-agent")

        assert result == "python"

    def test_matches_interests_no_interests(self, patch_data_dir):
        """Returns None when agent has no interests."""
        from src.agent.interests import matches_interests

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        result = matches_interests("any content", "test-agent")

        assert result is None


class TestGetAgentInterests:
    """Test getting interests for an agent."""

    def test_get_agent_interests_from_memory(self, patch_data_dir):
        """Gets interests from memory entries."""
        from src.agent.interests import get_agent_interests
        from src.tools.data.memory import add_memory

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        add_memory(short_description="python", type="interest", agent_id="test-agent")
        add_memory(short_description="machine learning", type="interest", agent_id="test-agent")

        interests = get_agent_interests("test-agent")

        assert "python" in interests
        assert "machine learning" in interests

    def test_get_agent_interests_excludes_non_interest_types(self, patch_data_dir):
        """Only returns interest-type memories."""
        from src.agent.interests import get_agent_interests
        from src.tools.data.memory import add_memory

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        add_memory(short_description="python", type="interest", agent_id="test-agent")
        add_memory(short_description="finish project", type="goal", agent_id="test-agent")

        interests = get_agent_interests("test-agent")

        assert "python" in interests
        assert "finish project" not in interests

    def test_get_agent_interests_deduplicates(self, patch_data_dir):
        """Returns deduplicated list."""
        from src.agent.interests import get_agent_interests
        from src.tools.data.memory import add_memory

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        add_memory(short_description="python", type="interest", agent_id="test-agent")
        add_memory(short_description="python", type="interest", agent_id="test-agent")

        interests = get_agent_interests("test-agent")

        assert interests.count("python") == 1


class TestGetObservingAgents:
    """Test getting agents with observation enabled."""

    def test_get_observing_agents_returns_enabled(self, patch_data_dir, create_test_agent):
        """Returns agents with observation.enabled=True."""
        from src.agent.interests import get_observing_agents

        create_test_agent("observer", observation={"enabled": True, "sources": ["chat"]})
        create_test_agent("non-observer")

        agents = get_observing_agents()

        agent_ids = [a["id"] for a in agents]
        assert "observer" in agent_ids
        assert "non-observer" not in agent_ids

    def test_get_observing_agents_empty_when_none(self, patch_data_dir):
        """Returns empty list when no observers."""
        from src.agent.interests import get_observing_agents

        agents = get_observing_agents()

        assert agents == []


class TestCheckContentForObservations:
    """Test checking content against all observers."""

    def test_check_content_creates_observations(self, patch_data_dir, create_test_agent):
        """Creates observations for matching content."""
        from src.agent.interests import check_content_for_observations
        from src.tools.data.memory import add_memory

        create_test_agent("observer", observation={"enabled": True, "sources": ["chat"]})

        agent_dir = patch_data_dir / "agents" / "observer" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)
        add_memory(short_description="python", type="interest", agent_id="observer")

        observations = check_content_for_observations(
            content="Learning Python today",
            source="chat"
        )

        assert len(observations) == 1
        assert observations[0].agent_id == "observer"
        assert observations[0].matched_keyword == "python"
        assert observations[0].source == "chat"

    def test_check_content_respects_source_filter(self, patch_data_dir, create_test_agent):
        """Respects agent's source filters."""
        from src.agent.interests import check_content_for_observations
        from src.tools.data.memory import add_memory

        # Only watches chat, not calendar
        create_test_agent("observer", observation={"enabled": True, "sources": ["chat"]})

        agent_dir = patch_data_dir / "agents" / "observer" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)
        add_memory(short_description="python", type="interest", agent_id="observer")

        observations = check_content_for_observations(
            content="Learning Python today",
            source="calendar"  # Not in sources
        )

        assert len(observations) == 0

    def test_check_content_excludes_specified_agents(self, patch_data_dir, create_test_agent):
        """Excludes agents in excluded_agents list."""
        from src.agent.interests import check_content_for_observations
        from src.tools.data.memory import add_memory

        create_test_agent("observer", observation={"enabled": True, "sources": ["chat"]})

        agent_dir = patch_data_dir / "agents" / "observer" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)
        add_memory(short_description="python", type="interest", agent_id="observer")

        observations = check_content_for_observations(
            content="Learning Python today",
            source="chat",
            excluded_agents=["observer"]
        )

        assert len(observations) == 0


class TestInterestCaching:
    """Test interest caching functionality."""

    def test_cache_returns_cached_value(self, patch_data_dir):
        """Cached interests are returned within TTL."""
        from src.agent.interests import (
            get_agent_interests_cached,
            invalidate_interest_cache,
            _interest_cache
        )
        from src.tools.data.memory import add_memory

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Clear cache first
        invalidate_interest_cache()

        add_memory(short_description="python", type="interest", agent_id="test-agent")

        # First call populates cache
        interests1 = get_agent_interests_cached("test-agent")

        # Add another interest (but cache won't see it)
        add_memory(short_description="javascript", type="interest", agent_id="test-agent")

        # Second call returns cached value
        interests2 = get_agent_interests_cached("test-agent")

        assert interests1 == interests2
        assert "javascript" not in interests2

    def test_invalidate_cache_clears_agent(self, patch_data_dir):
        """Invalidating cache for specific agent clears it."""
        from src.agent.interests import (
            get_agent_interests_cached,
            invalidate_interest_cache
        )
        from src.tools.data.memory import add_memory

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        add_memory(short_description="python", type="interest", agent_id="test-agent")

        # Populate cache
        get_agent_interests_cached("test-agent")

        # Add new interest
        add_memory(short_description="javascript", type="interest", agent_id="test-agent")

        # Invalidate and refetch
        invalidate_interest_cache("test-agent")
        interests = get_agent_interests_cached("test-agent")

        assert "javascript" in interests

    def test_invalidate_cache_all(self, patch_data_dir):
        """Invalidating all cache clears everything."""
        from src.agent.interests import (
            get_agent_interests_cached,
            invalidate_interest_cache,
            _interest_cache
        )
        from src.tools.data.memory import add_memory

        agent_dir = patch_data_dir / "agents" / "test-agent" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Clear any existing cache first
        invalidate_interest_cache()

        add_memory(short_description="python", type="interest", agent_id="test-agent")

        # Populate cache
        get_agent_interests_cached("test-agent")

        # Verify cache has entries
        assert len(_interest_cache) > 0

        # Invalidate all
        invalidate_interest_cache()

        # Cache should be empty
        assert len(_interest_cache) == 0
