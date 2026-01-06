"""
Event System - Central event bus for agent triggers and UI updates.

Events follow the format: {type}:{event}
Examples: job:assigned, lifelog:new, time:morning

Scoped events only wake the specific agent they're scoped to.
Unscoped events wake all agents subscribed to that event type.

UI events are broadcast to all connected SSE clients.
"""

import asyncio
import queue
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set


@dataclass
class Event:
    """An event that can trigger agents."""
    event: str              # e.g., "job:assigned"
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
            event: Event name (e.g., "job:assigned")
            scope: If set, only this agent_id receives the event
            data: Context data to include with the event
        """
        ev = Event(
            event=event,
            scope=scope,
            data=data or {},
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

        with self._lock:
            # Find agents subscribed to this event
            subscribers = self._subscriptions.get(event, set())

            for agent_id in subscribers:
                if ev.matches_trigger(event, agent_id):
                    q = self._agent_queues.get(agent_id)
                    if q:
                        q.put(ev)

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
    """Convenience function to emit an event."""
    bus = get_event_bus()
    if bus:
        bus.emit(event, scope=scope, data=data)


# ============== UI Event Broadcasting ==============
# For pushing updates to SSE clients

_ui_subscribers: List[asyncio.Queue] = []
_ui_lock = threading.Lock()


def subscribe_ui() -> asyncio.Queue:
    """Subscribe to UI events. Returns a queue that will receive events."""
    q = asyncio.Queue()
    with _ui_lock:
        _ui_subscribers.append(q)
    return q


def unsubscribe_ui(q: asyncio.Queue):
    """Unsubscribe from UI events."""
    with _ui_lock:
        if q in _ui_subscribers:
            _ui_subscribers.remove(q)


def emit_ui_event(event_type: str, data: dict = None):
    """Emit an event to all SSE clients.

    Args:
        event_type: Type of event (e.g., "jobs_update")
        data: Event data to send
    """
    with _ui_lock:
        for q in _ui_subscribers:
            try:
                q.put_nowait({"type": event_type, "data": data or {}})
            except asyncio.QueueFull:
                pass  # Skip if queue is full


def has_connected_clients() -> bool:
    """Check if any SSE clients are currently connected.

    Returns:
        True if at least one client is connected
    """
    with _ui_lock:
        return len(_ui_subscribers) > 0
