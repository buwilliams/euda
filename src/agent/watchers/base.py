"""
Base Watcher - Abstract base class for content watchers.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from ..interests import check_content_for_observations, Observation
from ...tools.data.topics import create_topic, list_topics
from ...tools.agents.agents import list_agents


logger = logging.getLogger(__name__)

# State file for tracking what watchers have seen
STATE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "system" / "watchers"


@dataclass
class WatcherState:
    """Persistent state for a watcher."""
    last_check: Optional[datetime] = None
    last_seen_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_seen_ids": self.last_seen_ids[-100:]  # Keep last 100 IDs
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WatcherState":
        last_check = None
        if data.get("last_check"):
            try:
                last_check = datetime.fromisoformat(data["last_check"])
            except ValueError:
                pass
        return cls(
            last_check=last_check,
            last_seen_ids=data.get("last_seen_ids", [])
        )


class Watcher(ABC):
    """Abstract base class for content watchers.

    Subclasses implement fetch_content() to retrieve content from their source.
    The base class handles state management, observation creation, and rate limiting.
    """

    source_name: str = "unknown"  # Override in subclass

    def __init__(self):
        self._state: Optional[WatcherState] = None

    @property
    def state_file(self) -> Path:
        """Path to this watcher's state file."""
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        return STATE_DIR / f"{self.source_name}.json"

    def load_state(self) -> WatcherState:
        """Load persisted state from disk."""
        if self._state is not None:
            return self._state

        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                self._state = WatcherState.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                self._state = WatcherState()
        else:
            self._state = WatcherState()

        return self._state

    def save_state(self):
        """Persist state to disk."""
        if self._state is None:
            return
        self.state_file.write_text(json.dumps(self._state.to_dict(), indent=2))

    @abstractmethod
    def fetch_content(self) -> list[dict]:
        """Fetch content from the source.

        Returns:
            List of content items, each with at least:
            - id: Unique identifier for deduplication
            - text: Content to match against interests
            - timestamp: When the content was created (optional)
        """
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if this watcher has valid configuration.

        Returns:
            True if the watcher can run, False if missing config
        """
        pass

    def check(self) -> list[Observation]:
        """Run a check cycle.

        Fetches new content, checks against interests, returns observations.

        Returns:
            List of observations for content that matched agent interests
        """
        if not self.is_configured():
            return []

        state = self.load_state()
        observations = []

        try:
            content_items = self.fetch_content()
        except Exception as e:
            logger.error(f"Watcher {self.source_name} fetch failed: {e}")
            return []

        for item in content_items:
            item_id = item.get("id", "")

            # Skip if already seen
            if item_id in state.last_seen_ids:
                continue

            text = item.get("text", "")
            if not text:
                continue

            # Check against all observing agents
            item_observations = check_content_for_observations(
                content=text,
                source=self.source_name
            )

            observations.extend(item_observations)

            # Mark as seen
            state.last_seen_ids.append(item_id)

        # Update state
        state.last_check = datetime.now()
        # Keep list bounded
        state.last_seen_ids = state.last_seen_ids[-100:]
        self._state = state
        self.save_state()

        return observations


class WatcherRegistry:
    """Registry of all watchers."""

    def __init__(self):
        self._watchers: dict[str, Watcher] = {}

    def register(self, watcher: Watcher):
        """Register a watcher."""
        self._watchers[watcher.source_name] = watcher

    def get(self, source_name: str) -> Optional[Watcher]:
        """Get a watcher by source name."""
        return self._watchers.get(source_name)

    def all(self) -> list[Watcher]:
        """Get all registered watchers."""
        return list(self._watchers.values())

    def check_all(self) -> list[Observation]:
        """Run check on all watchers.

        Returns:
            Combined list of observations from all watchers
        """
        observations = []
        for watcher in self._watchers.values():
            try:
                obs = watcher.check()
                observations.extend(obs)
            except Exception as e:
                logger.error(f"Watcher {watcher.source_name} failed: {e}")
        return observations


def create_observation_topic(observation: Observation) -> dict:
    """Create a topic for an observation.

    Checks rate limits before creating. Returns None if rate limited.

    Args:
        observation: The observation to create a topic for

    Returns:
        Created topic dict, or None if rate limited
    """
    agent_id = observation.agent_id

    # Check rate limits from agent config
    agent_config = _get_agent_config(agent_id)
    if not agent_config:
        return None

    obs_config = agent_config.get("observation", {})
    max_per_day = obs_config.get("max_per_day", 5)
    cooldown_minutes = obs_config.get("cooldown_minutes", 30)

    # Check existing observation topics for this agent today
    existing = list_topics(assignee=agent_id, tag="observation")
    today_count = sum(1 for t in existing if _is_today(t.get("created_at", "")))

    if today_count >= max_per_day:
        logger.debug(f"Agent {agent_id} at max observations for today ({max_per_day})")
        return None

    # Check cooldown (most recent observation)
    recent = [t for t in existing if _is_within_minutes(t.get("created_at", ""), cooldown_minutes)]
    if recent:
        logger.debug(f"Agent {agent_id} in cooldown period ({cooldown_minutes} min)")
        return None

    # Create the observation topic
    topic_name = f"observation:{observation.source}:{observation.timestamp[:19]}"
    description = (
        f"**Source:** {observation.source}\n"
        f"**Matched:** \"{observation.matched_keyword}\"\n\n"
        f"**Content:**\n{observation.content[:500]}"
    )

    topic = create_topic(
        name=topic_name,
        description=description,
        tags=["observation", f"source:{observation.source}"],
        assignee=agent_id,
        created_by="system"
    )

    logger.info(f"Created observation topic for {agent_id}: {topic_name}")
    return topic


def process_observations(observations: list[Observation]) -> list[dict]:
    """Process a list of observations, creating topics as appropriate.

    Handles rate limiting per agent.

    Args:
        observations: List of observations to process

    Returns:
        List of created topic dicts
    """
    created = []
    for obs in observations:
        topic = create_observation_topic(obs)
        if topic:
            created.append(topic)
    return created


def _get_agent_config(agent_id: str) -> dict:
    """Get agent config by ID."""
    for agent in list_agents():
        if agent.get("id") == agent_id:
            return agent
    return None


def _is_today(timestamp: str) -> bool:
    """Check if timestamp is from today."""
    if not timestamp:
        return False
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.date() == datetime.now().date()
    except ValueError:
        return False


def _is_within_minutes(timestamp: str, minutes: int) -> bool:
    """Check if timestamp is within the last N minutes."""
    if not timestamp:
        return False
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        cutoff = datetime.now(dt.tzinfo) - timedelta(minutes=minutes)
        return dt > cutoff
    except ValueError:
        return False
