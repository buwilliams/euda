"""
Core Event System - Central event bus for agent coordination and system events.

Used by: agents, tools, web routes, CLI, integrations.

UI events (SSE to browsers) remain in src/web/events.py.
Dev CLI events (for watch command) remain in src/web/events.py.
"""

import queue
import threading
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Dict, List, Optional, Set


@dataclass
class Event:
    """An event that can trigger agents."""
    event: str              # e.g., "topic:assigned", "system:start"
    scope: Optional[str]    # agent_id if scoped, None if broadcast
    data: dict              # context data
    timestamp: str          # ISO timestamp

    def matches_trigger(self, trigger: str, agent_id: str) -> bool:
        """Check if this event matches a trigger for an agent."""
        if self.event != trigger:
            return False
        # If scoped, only match the scoped agent
        if self.scope is not None:
            return self.scope == agent_id
        return True


class EventBus:
    """Central event bus for routing events to agents."""

    def __init__(self):
        self._subscriptions: Dict[str, Set[str]] = {}  # trigger -> set of agent_ids
        self._agent_queues: Dict[str, queue.Queue] = {}
        self._lock = threading.Lock()

    def subscribe(self, agent_id: str, triggers: List[str]):
        """Subscribe an agent to triggers."""
        with self._lock:
            # Create queue for agent
            if agent_id not in self._agent_queues:
                self._agent_queues[agent_id] = queue.Queue()

            # Register subscriptions
            for trigger in triggers:
                if trigger not in self._subscriptions:
                    self._subscriptions[trigger] = set()
                self._subscriptions[trigger].add(agent_id)

    def unsubscribe(self, agent_id: str):
        """Remove all subscriptions for an agent."""
        with self._lock:
            # Remove from all subscription lists
            for trigger in list(self._subscriptions.keys()):
                self._subscriptions[trigger].discard(agent_id)
                if not self._subscriptions[trigger]:
                    del self._subscriptions[trigger]

            # Remove queue
            if agent_id in self._agent_queues:
                del self._agent_queues[agent_id]

    def emit(self, event: str, scope: str = None, data: dict = None):
        """Emit an event.

        Args:
            event: Event name (e.g., "topic:assigned", "system:start")
            scope: If set, only this agent_id receives the event
            data: Context data to include with the event
        """
        ev = Event(
            event=event,
            scope=scope,
            data=data or {},
            timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z")
        )

        with self._lock:
            # Find agents subscribed to this event
            subscribers = self._subscriptions.get(event, set())

            for agent_id in subscribers:
                if ev.matches_trigger(event, agent_id):
                    q = self._agent_queues.get(agent_id)
                    if q:
                        q.put(ev)

    def get_event_nonblocking(self, agent_id: str) -> Optional[Event]:
        """Get next event for this agent without blocking.

        Args:
            agent_id: The agent checking for events

        Returns:
            Event object if available, None otherwise
        """
        q = self._agent_queues.get(agent_id)
        if not q:
            return None

        try:
            return q.get_nowait()
        except queue.Empty:
            return None

    def wait_for_event(self, agent_id: str, timeout: float = None) -> Optional[dict]:
        """Wait for next event for this agent.

        Args:
            agent_id: The agent waiting for events
            timeout: Max seconds to wait (None = wait forever)

        Returns:
            Event as dict with keys: event, data, timestamp
            None if timeout or agent not subscribed
        """
        q = self._agent_queues.get(agent_id)
        if not q:
            return None

        try:
            event = q.get(timeout=timeout)
            return {
                "event": event.event,
                "data": event.data,
                "timestamp": event.timestamp
            }
        except queue.Empty:
            return None

    def get_subscriptions(self, agent_id: str) -> List[str]:
        """Get list of triggers an agent is subscribed to."""
        with self._lock:
            triggers = []
            for trigger, agents in self._subscriptions.items():
                if agent_id in agents:
                    triggers.append(trigger)
            return triggers


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> Optional[EventBus]:
    """Get the global event bus instance."""
    return _event_bus


def set_event_bus(bus: EventBus):
    """Set the global event bus instance."""
    global _event_bus
    _event_bus = bus


def emit_event(event: str, scope: str = None, data: dict = None):
    """Convenience function to emit an event to the EventBus.

    This emits to the EventBus for agent subscriptions.
    Does NOT emit to dev CLI watchers - use emit_system_event for that.
    """
    bus = get_event_bus()
    if bus:
        bus.emit(event, scope=scope, data=data)


def emit_system_event(event: str, data: dict = None, source: str = "system"):
    """Emit a system event for trigger matching.

    This is the canonical way to emit events that agents can trigger on.
    Use this for: system:start, chat:message_received, topic:created,
    topic:completed, and any future system events.

    Args:
        event: Event name (e.g., "system:start", "topic:created")
        data: Context data for the event
        source: Origin of event (for loop prevention, e.g., "trigger")
    """
    bus = get_event_bus()
    if bus:
        event_data = data.copy() if data else {}
        event_data["_source"] = source
        bus.emit(event, data=event_data)

    # Broadcast to dev CLI watchers
    from .web.events import emit_dev_event, has_dev_subscribers
    if has_dev_subscribers():
        emit_dev_event(source, event, data)
