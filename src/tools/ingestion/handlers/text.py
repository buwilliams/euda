"""
Text file handler for plain text, markdown, and similar files.
"""

import os
from pathlib import Path
from datetime import datetime

from .base import FileHandler, register_handler


@register_handler
class TextHandler(FileHandler):
    """Handler for text-based files."""

    categories = ["text"]

    # Maximum chars to send to AI for large files
    MAX_CONTENT_LENGTH = 50000

    def extract_metadata(self, file_path: str) -> dict:
        """Extract metadata from a text file."""
        path = Path(file_path)
        stat = path.stat()

        # Try to detect encoding and count lines without loading entire file
        line_count = 0
        encoding = "utf-8"
        preview_lines = []

        try:
            with open(path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    line_count += 1
                    if i < 10:  # First 10 lines as preview
                        preview_lines.append(line.rstrip())
        except UnicodeDecodeError:
            # Try latin-1 as fallback
            encoding = "latin-1"
            try:
                with open(path, 'r', encoding='latin-1') as f:
                    for i, line in enumerate(f):
                        line_count += 1
                        if i < 10:
                            preview_lines.append(line.rstrip())
            except Exception:
                pass

        return {
            "type": "text",
            "size_bytes": stat.st_size,
            "line_count": line_count,
            "encoding": encoding,
            "extension": path.suffix.lower(),
            "preview": preview_lines[:5],
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    def prepare_for_ai(self, file_path: str, metadata: dict) -> str:
        """Prepare text content for AI processing."""
        path = Path(file_path)
        encoding = metadata.get("encoding", "utf-8")
        size = metadata.get("size_bytes", 0)

        try:
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
        except Exception as e:
            return f"Error reading file: {e}"

        # Truncate if too large
        if len(content) > self.MAX_CONTENT_LENGTH:
            # Take beginning and end
            half = self.MAX_CONTENT_LENGTH // 2
            content = (
                content[:half] +
                f"\n\n[... {len(content) - self.MAX_CONTENT_LENGTH} characters truncated ...]\n\n" +
                content[-half:]
            )

        return content

    def estimate_tokens(self, metadata: dict) -> int:
        """Estimate tokens for text processing."""
        size = metadata.get("size_bytes", 0)
        # Rough estimate: 4 characters per token
        estimated = size // 4

        # Cap at what we'd actually send
        max_tokens = self.MAX_CONTENT_LENGTH // 4
        return min(estimated, max_tokens) + 100  # +100 for overhead

    def get_temporal_hints(self, file_path: str, metadata: dict) -> dict:
        """Extract temporal hints from text file."""
        # Use file modification time as fallback
        modified = metadata.get("modified_time")
        if modified:
            return {
                "timestamp": modified,
                "confidence": "low",
                "source": "file_mtime"
            }
        return super().get_temporal_hints(file_path, metadata)
