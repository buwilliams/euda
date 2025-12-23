"""
Base class for file handlers.

Each handler implements type-specific logic for:
- Metadata extraction (local, no AI)
- Content preparation for AI
- Token estimation
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class FileHandler(ABC):
    """
    Abstract base class for file type handlers.

    Subclasses implement handling for specific file types like
    images, PDFs, audio, video, etc.
    """

    # Categories this handler can process
    categories: list[str] = []

    @classmethod
    def can_handle(cls, category: str) -> bool:
        """Check if this handler can process the given category."""
        return category in cls.categories

    @abstractmethod
    def extract_metadata(self, file_path: str) -> dict:
        """
        Extract metadata from the file WITHOUT loading full content.

        This should be fast and memory-efficient, extracting only
        headers, dimensions, page counts, etc.

        Returns:
            Dict with type-specific metadata
        """
        pass

    @abstractmethod
    def prepare_for_ai(self, file_path: str, metadata: dict) -> str:
        """
        Prepare file content for AI processing.

        For large files, this may return a summary or key excerpts
        rather than the full content.

        Args:
            file_path: Path to the file
            metadata: Previously extracted metadata

        Returns:
            String content suitable for AI processing
        """
        pass

    @abstractmethod
    def estimate_tokens(self, metadata: dict) -> int:
        """
        Estimate tokens needed to process this file.

        Args:
            metadata: Previously extracted metadata

        Returns:
            Estimated token count
        """
        pass

    def get_temporal_hints(self, file_path: str, metadata: dict) -> dict:
        """
        Extract temporal information from the file.

        Returns dict with:
            - timestamp: ISO format datetime if found
            - confidence: high/medium/low
            - source: where the timestamp came from
        """
        # Default implementation - subclasses can override
        return {
            "timestamp": None,
            "confidence": "low",
            "source": "none"
        }


# Handler registry
_handlers: list[type[FileHandler]] = []


def register_handler(handler_class: type[FileHandler]):
    """Register a handler class."""
    _handlers.append(handler_class)
    return handler_class


def get_handler(category: str) -> Optional[FileHandler]:
    """
    Get a handler instance for the given category.

    Returns:
        Handler instance or None if no handler found
    """
    for handler_class in _handlers:
        if handler_class.can_handle(category):
            return handler_class()
    return None


def get_all_handlers() -> list[FileHandler]:
    """Get instances of all registered handlers."""
    return [cls() for cls in _handlers]
