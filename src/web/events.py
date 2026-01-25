"""
Event System - Central event bus for agent triggers and UI updates.

Events follow the format: {type}:{event}
Examples: topic:assigned, memory:long-term, time:morning

Scoped events only wake the specific agent they're scoped to.
Unscoped events wake all agents subscribed to that event type.

UI events are broadcast to all connected SSE clients.
"""

import asyncio
import queue
import threading
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Dict, List, Optional, Set


@dataclass
class Event:
    """An event that can trigger agents."""
    event: str              # e.g., "topic:assigned"
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
            event: Event name (e.g., "topic:assigned")
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

    # Also broadcast to dev CLI watchers if any are connected
    if has_dev_subscribers():
        emit_dev_event(scope or "system", event, data)


# ============== UI Event Broadcasting ==============
# For pushing updates to SSE clients

_ui_subscribers: List[asyncio.Queue] = []
_ui_shutdown_events: List[asyncio.Event] = []  # One event per subscriber for immediate wakeup
_ui_lock = threading.Lock()


def subscribe_ui() -> tuple:
    """Subscribe to UI events. Returns (queue, shutdown_event) tuple."""
    q = asyncio.Queue()
    shutdown_event = asyncio.Event()
    with _ui_lock:
        _ui_subscribers.append(q)
        _ui_shutdown_events.append(shutdown_event)
    return q, shutdown_event


def unsubscribe_ui(q: asyncio.Queue, shutdown_event: asyncio.Event):
    """Unsubscribe from UI events."""
    with _ui_lock:
        if q in _ui_subscribers:
            _ui_subscribers.remove(q)
        if shutdown_event in _ui_shutdown_events:
            _ui_shutdown_events.remove(shutdown_event)


def trigger_shutdown():
    """Signal all SSE connections to close immediately."""
    with _ui_lock:
        # Set all shutdown events to wake up any waiting generators
        for event in _ui_shutdown_events:
            event.set()


def emit_ui_event(event_type: str, data: dict = None):
    """Emit an event to all SSE clients.

    Args:
        event_type: Type of event (e.g., "topics_update")
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


# ============== Dev CLI Event Broadcasting ==============
# For dev CLI watch command to see all system events

_dev_subscribers: List[queue.Queue] = []
_dev_lock = threading.Lock()


def subscribe_dev() -> queue.Queue:
    """Subscribe to all events for dev CLI watch mode.

    Returns:
        Queue that receives all events
    """
    q = queue.Queue(maxsize=1000)
    with _dev_lock:
        _dev_subscribers.append(q)
    return q


def unsubscribe_dev(q: queue.Queue):
    """Unsubscribe from dev events."""
    with _dev_lock:
        if q in _dev_subscribers:
            _dev_subscribers.remove(q)


def emit_dev_event(source: str, event: str, data: dict = None):
    """Emit an event to all dev CLI subscribers.

    Args:
        source: Source of event (agent_id or "system")
        event: Event type
        data: Event data
    """
    entry = {
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source": source,
        "event": event,
        "data": data or {}
    }
    with _dev_lock:
        for q in list(_dev_subscribers):
            try:
                q.put_nowait(entry)
            except queue.Full:
                pass  # Skip if queue is full


def has_dev_subscribers() -> bool:
    """Check if any dev CLI watchers are connected."""
    with _dev_lock:
        return len(_dev_subscribers) > 0
