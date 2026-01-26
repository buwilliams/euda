"""
Unit tests for watcher module.

Tests for src/agent/watchers/
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


class TestWatcherState:
    """Test WatcherState dataclass."""

    def test_to_dict(self):
        """WatcherState serializes to dict."""
        from src.agent.watchers.base import WatcherState

        now = datetime.now()
        state = WatcherState(
            last_check=now,
            last_seen_ids=["id1", "id2"]
        )

        data = state.to_dict()

        assert data["last_check"] == now.isoformat()
        assert data["last_seen_ids"] == ["id1", "id2"]

    def test_to_dict_none_last_check(self):
        """WatcherState handles None last_check."""
        from src.agent.watchers.base import WatcherState

        state = WatcherState()
        data = state.to_dict()

        assert data["last_check"] is None
        assert data["last_seen_ids"] == []

    def test_from_dict(self):
        """WatcherState deserializes from dict."""
        from src.agent.watchers.base import WatcherState

        now = datetime.now()
        data = {
            "last_check": now.isoformat(),
            "last_seen_ids": ["id1", "id2"]
        }

        state = WatcherState.from_dict(data)

        assert state.last_check == now
        assert state.last_seen_ids == ["id1", "id2"]

    def test_from_dict_handles_missing_fields(self):
        """WatcherState handles missing fields in dict."""
        from src.agent.watchers.base import WatcherState

        state = WatcherState.from_dict({})

        assert state.last_check is None
        assert state.last_seen_ids == []

    def test_from_dict_handles_invalid_date(self):
        """WatcherState handles invalid date format."""
        from src.agent.watchers.base import WatcherState

        state = WatcherState.from_dict({"last_check": "not-a-date"})

        assert state.last_check is None

    def test_last_seen_ids_bounded_at_100(self):
        """last_seen_ids is bounded to 100 items in to_dict."""
        from src.agent.watchers.base import WatcherState

        state = WatcherState(
            last_seen_ids=[f"id{i}" for i in range(150)]
        )

        data = state.to_dict()

        assert len(data["last_seen_ids"]) == 100
        # Should keep the last 100
        assert data["last_seen_ids"][0] == "id50"


class TestWatcherRegistry:
    """Test WatcherRegistry."""

    def test_register_and_get(self):
        """Can register and retrieve watchers."""
        from src.agent.watchers.base import WatcherRegistry, Watcher

        class TestWatcher(Watcher):
            source_name = "test"
            def fetch_content(self): return []
            def is_configured(self): return True

        registry = WatcherRegistry()
        watcher = TestWatcher()

        registry.register(watcher)
        retrieved = registry.get("test")

        assert retrieved is watcher

    def test_get_unknown_returns_none(self):
        """Getting unknown watcher returns None."""
        from src.agent.watchers.base import WatcherRegistry

        registry = WatcherRegistry()

        assert registry.get("unknown") is None

    def test_all_returns_all_watchers(self):
        """all() returns all registered watchers."""
        from src.agent.watchers.base import WatcherRegistry, Watcher

        class TestWatcher1(Watcher):
            source_name = "test1"
            def fetch_content(self): return []
            def is_configured(self): return True

        class TestWatcher2(Watcher):
            source_name = "test2"
            def fetch_content(self): return []
            def is_configured(self): return True

        registry = WatcherRegistry()
        registry.register(TestWatcher1())
        registry.register(TestWatcher2())

        all_watchers = registry.all()

        assert len(all_watchers) == 2


class TestWatcherBase:
    """Test Watcher base class."""

    def test_check_skips_unconfigured(self, patch_data_dir):
        """check() skips if not configured."""
        from src.agent.watchers.base import Watcher

        class UnconfiguredWatcher(Watcher):
            source_name = "unconfigured"
            def fetch_content(self): return [{"id": "1", "text": "test"}]
            def is_configured(self): return False

        watcher = UnconfiguredWatcher()
        observations = watcher.check()

        assert observations == []

    def test_check_skips_already_seen(self, patch_data_dir, create_test_agent):
        """check() skips already seen items."""
        from src.agent.watchers.base import Watcher, WatcherState
        from src.tools.data.memory import add_memory

        create_test_agent("observer", observation={"enabled": True, "sources": ["test"]})

        agent_dir = patch_data_dir / "agents" / "observer" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)
        add_memory(short_description="keyword", type="interest", agent_id="observer")

        class TestWatcher(Watcher):
            source_name = "test"
            def fetch_content(self):
                return [{"id": "seen-id", "text": "some keyword here"}]
            def is_configured(self):
                return True

        watcher = TestWatcher()
        # Pre-populate seen IDs
        watcher._state = WatcherState(last_seen_ids=["seen-id"])

        observations = watcher.check()

        assert observations == []

    def test_check_finds_new_matches(self, patch_data_dir, create_test_agent):
        """check() creates observations for new matching content."""
        from src.agent.watchers.base import Watcher

        create_test_agent("observer", observation={"enabled": True, "sources": ["test"]})

        # Create memory directory and add interest
        from src.tools.data.memory import add_memory
        agent_dir = patch_data_dir / "agents" / "observer" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)
        add_memory(short_description="python", type="interest", agent_id="observer")

        class TestWatcher(Watcher):
            source_name = "test"
            def fetch_content(self):
                return [{"id": "new-id", "text": "learning python today"}]
            def is_configured(self):
                return True

        watcher = TestWatcher()
        observations = watcher.check()

        assert len(observations) == 1
        assert observations[0].matched_keyword == "python"
        assert observations[0].agent_id == "observer"

    def test_check_marks_items_as_seen(self, patch_data_dir, create_test_agent):
        """check() marks processed items as seen."""
        from src.agent.watchers.base import Watcher

        create_test_agent("observer", observation={"enabled": True, "sources": ["test"]})

        from src.tools.data.memory import add_memory
        agent_dir = patch_data_dir / "agents" / "observer" / "memory"
        agent_dir.mkdir(parents=True, exist_ok=True)
        add_memory(short_description="python", type="interest", agent_id="observer")

        class TestWatcher(Watcher):
            source_name = "test"
            def fetch_content(self):
                return [{"id": "item-1", "text": "learning python"}]
            def is_configured(self):
                return True

        watcher = TestWatcher()
        watcher.check()

        assert "item-1" in watcher._state.last_seen_ids


class TestRateLimiting:
    """Test observation rate limiting."""

    def test_is_today(self):
        """_is_today correctly identifies today's timestamps."""
        from src.agent.watchers.base import _is_today

        today = datetime.now().isoformat()
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()

        assert _is_today(today) is True
        assert _is_today(yesterday) is False
        assert _is_today("") is False
        assert _is_today("invalid") is False

    def test_is_within_minutes(self):
        """_is_within_minutes correctly checks time window."""
        from src.agent.watchers.base import _is_within_minutes

        now = datetime.now().isoformat()
        hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()

        assert _is_within_minutes(now, 30) is True
        assert _is_within_minutes(hour_ago, 30) is False
        assert _is_within_minutes("", 30) is False

    def test_create_observation_topic_respects_max_per_day(self, patch_data_dir, test_db, create_test_agent):
        """create_observation_topic respects max_per_day limit."""
        from src.agent.watchers.base import create_observation_topic
        from src.agent.interests import Observation
        from src.tools.data.topics import create_topic

        create_test_agent("observer", observation={
            "enabled": True,
            "sources": ["chat"],
            "max_per_day": 2,
            "cooldown_minutes": 0
        })

        # Create 2 existing observation topics for today
        for i in range(2):
            create_topic(
                name=f"observation:test:{datetime.now().isoformat()[:19]}",
                tags=["observation"],
                assignee="observer",
                created_by="system"
            )

        # Try to create another
        obs = Observation(
            agent_id="observer",
            source="chat",
            content="test content",
            matched_keyword="test"
        )

        result = create_observation_topic(obs)

        assert result is None  # Rate limited

    def test_create_observation_topic_respects_cooldown(self, patch_data_dir, test_db, create_test_agent):
        """create_observation_topic respects cooldown_minutes."""
        from src.agent.watchers.base import create_observation_topic
        from src.agent.interests import Observation
        from src.tools.data.topics import create_topic

        create_test_agent("observer", observation={
            "enabled": True,
            "sources": ["chat"],
            "max_per_day": 10,
            "cooldown_minutes": 60  # 1 hour cooldown
        })

        # Create a recent observation topic
        create_topic(
            name=f"observation:test:{datetime.now().isoformat()[:19]}",
            tags=["observation"],
            assignee="observer",
            created_by="system"
        )

        # Try to create another within cooldown
        obs = Observation(
            agent_id="observer",
            source="chat",
            content="test content",
            matched_keyword="test"
        )

        result = create_observation_topic(obs)

        assert result is None  # Rate limited by cooldown

    def test_create_observation_topic_creates_when_allowed(self, patch_data_dir, test_db, create_test_agent):
        """create_observation_topic creates topic when not rate limited."""
        from src.agent.watchers.base import create_observation_topic
        from src.agent.interests import Observation

        create_test_agent("observer", observation={
            "enabled": True,
            "sources": ["chat"],
            "max_per_day": 10,
            "cooldown_minutes": 0
        })

        obs = Observation(
            agent_id="observer",
            source="chat",
            content="test content about python",
            matched_keyword="python"
        )

        result = create_observation_topic(obs)

        assert result is not None
        assert "observation:" in result["name"]
        assert result["assignee"] == "observer"
        assert "observation" in result["tags"]


class TestProcessObservations:
    """Test processing multiple observations."""

    def test_process_observations_creates_topics(self, patch_data_dir, test_db, create_test_agent):
        """process_observations creates topics for each observation."""
        from src.agent.watchers.base import process_observations
        from src.agent.interests import Observation

        create_test_agent("observer1", observation={
            "enabled": True,
            "sources": ["chat"],
            "max_per_day": 10,
            "cooldown_minutes": 0
        })
        create_test_agent("observer2", observation={
            "enabled": True,
            "sources": ["chat"],
            "max_per_day": 10,
            "cooldown_minutes": 0
        })

        observations = [
            Observation(agent_id="observer1", source="chat", content="test1", matched_keyword="kw1"),
            Observation(agent_id="observer2", source="chat", content="test2", matched_keyword="kw2"),
        ]

        created = process_observations(observations)

        assert len(created) == 2

    def test_process_observations_handles_rate_limits(self, patch_data_dir, test_db, create_test_agent):
        """process_observations skips rate-limited agents."""
        from src.agent.watchers.base import process_observations
        from src.agent.interests import Observation

        create_test_agent("observer", observation={
            "enabled": True,
            "sources": ["chat"],
            "max_per_day": 0,  # Already at limit
            "cooldown_minutes": 0
        })

        observations = [
            Observation(agent_id="observer", source="chat", content="test", matched_keyword="kw"),
        ]

        created = process_observations(observations)

        assert len(created) == 0
