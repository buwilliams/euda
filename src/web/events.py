"""
UI Event Broadcasting - SSE events for connected web clients and dev CLI watchers.

Core event infrastructure (EventBus, Event) is in src/events.py.
This module handles:
- UI events (SSE to browsers)
- Dev CLI events (for watch command)
"""

import asyncio
import queue
import threading
from datetime import datetime, UTC
from typing import List

# Re-export core event functions for backwards compatibility
from ..events import (
    Event,
    EventBus,
    get_event_bus,
    set_event_bus,
    emit_event,
    emit_system_event,
)

__all__ = [
    # Core event system (re-exported from src.events)
    "Event",
    "EventBus",
    "get_event_bus",
    "set_event_bus",
    "emit_event",
    "emit_system_event",
    # UI events
    "subscribe_ui",
    "unsubscribe_ui",
    "emit_ui_event",
    "has_connected_clients",
    "trigger_shutdown",
    # Dev CLI events
    "subscribe_dev",
    "unsubscribe_dev",
    "emit_dev_event",
    "has_dev_subscribers",
]


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
