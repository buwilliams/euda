"""
Base Sync Handler - Interface for data-type specific sync handlers.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple

from ..transport import Transport
from ..conflicts import Conflict


class SyncHandler(ABC):
    """Base class for sync handlers.

    Each handler is responsible for a specific type of data
    (files, topics, memory, etc.) and knows how to:
    1. Detect changes between local and remote
    2. Detect conflicts
    3. Apply changes in both directions
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Handler name for logging and error messages."""
        pass

    @abstractmethod
    def detect_changes(
        self,
        transport: Transport,
        direction: str,
    ) -> Tuple[List["SyncChange"], List[Conflict]]:
        """Detect changes between local and remote.

        Args:
            transport: Transport for remote access
            direction: "push", "pull", or "bidirectional"

        Returns:
            Tuple of (changes, conflicts)
            - changes: List of SyncChange objects describing what needs to be synced
            - conflicts: List of Conflict objects that need user resolution
        """
        pass

    @abstractmethod
    def apply_changes(
        self,
        transport: Transport,
        direction: str,
        changes: List["SyncChange"],
    ) -> None:
        """Apply changes to local and/or remote.

        Only applies changes that belong to this handler.
        Sets applied=True on each change after successful application.

        Args:
            transport: Transport for remote access
            direction: "push", "pull", or "bidirectional"
            changes: List of all SyncChange objects (filter for this handler)
        """
        pass


# Import SyncChange here to avoid circular import issues
from ..sync import SyncChange  # noqa: E402
