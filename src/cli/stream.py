"""
Event streaming utilities for dev CLI.

Provides EventStream for capturing and displaying agent events in real-time.
"""

import threading
from datetime import datetime
from queue import Queue, Empty
from typing import Callable, Optional

from .formatters import format_human, format_json


class EventStream:
    """Manages event streaming from agent execution.

    Provides an event sink callback that can be passed to Agent,
    and a print loop that displays events as they arrive.
    """

    def __init__(self, json_mode: bool = False):
        """Initialize EventStream.

        Args:
            json_mode: If True, output JSON format; otherwise human-readable
        """
        self.json_mode = json_mode
        self._queue: Queue = Queue()
        self._running = False
        self._print_thread: Optional[threading.Thread] = None

    def sink(self, event: str, data: Optional[dict] = None):
        """Event sink callback for Agent.

        This is the callback passed to Agent's event_sink parameter.

        Args:
            event: Event type name
            data: Event data dictionary
        """
        entry = {
            "event": event,
            "timestamp": datetime.now().isoformat(),
            **(data or {})
        }
        self._queue.put(entry)

    def _format(self, event: str, data: dict) -> str:
        """Format an event for output.

        Args:
            event: Event type name
            data: Event data dictionary

        Returns:
            Formatted string
        """
        if self.json_mode:
            return format_json(event, data)
        else:
            return format_human(event, data)

    def _print_loop(self):
        """Print events as they arrive (runs in background thread)."""
        while self._running:
            try:
                entry = self._queue.get(timeout=0.1)
                event = entry.pop("event", "unknown")
                line = self._format(event, entry)
                print(line, flush=True)
            except Empty:
                continue
            except Exception:
                # Don't let print errors stop the loop
                continue

    def start(self):
        """Start the background print loop."""
        if self._running:
            return

        self._running = True
        self._print_thread = threading.Thread(target=self._print_loop, daemon=True)
        self._print_thread.start()

    def stop(self):
        """Stop the print loop."""
        self._running = False
        if self._print_thread:
            self._print_thread.join(timeout=1.0)
            self._print_thread = None

    def drain(self):
        """Print any remaining events in the queue."""
        while True:
            try:
                entry = self._queue.get_nowait()
                event = entry.pop("event", "unknown")
                line = self._format(event, entry)
                print(line, flush=True)
            except Empty:
                break
            except Exception:
                continue

    def flush(self):
        """Stop the print loop and drain remaining events."""
        self.stop()
        self.drain()

    def __enter__(self):
        """Context manager entry - start streaming."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stop and drain."""
        self.flush()
        return False


class SyncEventStream:
    """Synchronous event stream for single-threaded execution.

    Prints events immediately without background threading.
    Useful for simpler commands that don't need async output.
    """

    def __init__(self, json_mode: bool = False):
        """Initialize SyncEventStream.

        Args:
            json_mode: If True, output JSON format; otherwise human-readable
        """
        self.json_mode = json_mode

    def sink(self, event: str, data: Optional[dict] = None):
        """Event sink callback - prints immediately.

        Args:
            event: Event type name
            data: Event data dictionary
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            **(data or {})
        }

        if self.json_mode:
            line = format_json(event, entry)
        else:
            line = format_human(event, entry)

        print(line, flush=True)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        return False


def create_event_sink(json_mode: bool = False, sync: bool = False) -> tuple:
    """Create an event sink and stream.

    Args:
        json_mode: If True, output JSON format
        sync: If True, use synchronous stream (no threading)

    Returns:
        Tuple of (sink_callback, stream_object)
    """
    if sync:
        stream = SyncEventStream(json_mode)
    else:
        stream = EventStream(json_mode)

    return stream.sink, stream
