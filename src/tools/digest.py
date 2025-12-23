"""
Digest Generator for Ingestion Agent.

Creates file digests (metadata summaries) that can be used for:
- Priority scoring
- Token estimation
- Duplicate detection
- Temporal hints

Digests are cached to avoid re-processing unchanged files.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .classifier import classify_file, compute_file_hash
from .handlers import get_handler


# Data paths
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "ingestion"
DIGESTS_DIR = DATA_DIR / "digests"


def ensure_dirs():
    """Ensure digest directories exist."""
    DIGESTS_DIR.mkdir(parents=True, exist_ok=True)


def get_digest_path(file_hash: str) -> Path:
    """Get the path for a digest file."""
    return DIGESTS_DIR / f"{file_hash}.json"


def load_digest(file_hash: str) -> Optional[dict]:
    """Load a cached digest if it exists."""
    digest_path = get_digest_path(file_hash)
    if digest_path.exists():
        with open(digest_path, 'r') as f:
            return json.load(f)
    return None


def save_digest(file_hash: str, digest: dict):
    """Save a digest to cache."""
    ensure_dirs()
    digest_path = get_digest_path(file_hash)
    with open(digest_path, 'w') as f:
        json.dump(digest, f, indent=2)


def generate_digest(file_path: str, force: bool = False) -> dict:
    """
    Generate a digest for a file.

    The digest includes:
    - Classification info (type, category, etc.)
    - Handler-specific metadata
    - Token estimates
    - Temporal hints

    Args:
        file_path: Path to the file
        force: If True, regenerate even if cached

    Returns:
        Complete digest dict
    """
    # First, classify the file
    classification = classify_file(file_path)

    # Check for cached digest
    file_hash = classification.get("file_hash", "")
    if file_hash and not force:
        cached = load_digest(file_hash)
        if cached:
            # Verify file hasn't changed
            if cached.get("classification", {}).get("file_hash") == file_hash:
                return cached

    # Build the digest
    digest = {
        "generated_at": datetime.now().isoformat(),
        "classification": classification,
        "metadata": {},
        "temporal_hints": {},
        "token_estimate": 0,
        "content_preview": "",
    }

    # If file should be ignored or is duplicate, return minimal digest
    if classification.get("should_ignore"):
        digest["status"] = "ignored"
        digest["status_reason"] = classification.get("ignore_reason", "")
        return digest

    if classification.get("is_duplicate"):
        digest["status"] = "duplicate"
        digest["status_reason"] = f"Already processed (hash: {file_hash[:16]}...)"
        return digest

    # Get the appropriate handler
    category = classification.get("category", "unknown")
    handler = get_handler(category)

    if handler:
        try:
            # Extract metadata
            metadata = handler.extract_metadata(file_path)
            digest["metadata"] = metadata

            # Get temporal hints
            temporal = handler.get_temporal_hints(file_path, metadata)
            digest["temporal_hints"] = temporal

            # Estimate tokens
            digest["token_estimate"] = handler.estimate_tokens(metadata)

        except Exception as e:
            digest["metadata_error"] = str(e)
            # Fallback token estimate based on file size
            size = classification.get("size", 0)
            digest["token_estimate"] = max(100, size // 4)
    else:
        # No handler - use basic estimates
        size = classification.get("size", 0)
        digest["token_estimate"] = max(100, size // 4)
        digest["metadata"]["note"] = f"No handler for category: {category}"

    # Set status
    digest["status"] = "ready"

    # Cache the digest
    if file_hash:
        save_digest(file_hash, digest)

    return digest


def get_content_for_ai(file_path: str, digest: Optional[dict] = None) -> str:
    """
    Get the content string to send to AI for processing.

    Uses the handler to prepare appropriate content based on file type.

    Args:
        file_path: Path to the file
        digest: Optional pre-generated digest

    Returns:
        Content string for AI processing
    """
    if digest is None:
        digest = generate_digest(file_path)

    # Check if file is ready for processing
    status = digest.get("status", "")
    if status == "ignored":
        return f"[File ignored: {digest.get('status_reason', 'unknown reason')}]"
    if status == "duplicate":
        return f"[File is duplicate: {digest.get('status_reason', '')}]"

    # Get handler
    category = digest.get("classification", {}).get("category", "unknown")
    handler = get_handler(category)

    if handler:
        try:
            metadata = digest.get("metadata", {})
            return handler.prepare_for_ai(file_path, metadata)
        except Exception as e:
            return f"[Error preparing content: {e}]"

    # Fallback: try to read as text
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if len(content) > 50000:
            content = content[:25000] + "\n\n[...truncated...]\n\n" + content[-25000:]
        return content
    except Exception as e:
        return f"[Could not read file: {e}]"


def get_digest_summary(file_path: str) -> str:
    """Get a human-readable summary of a file's digest."""
    digest = generate_digest(file_path)

    classification = digest.get("classification", {})
    metadata = digest.get("metadata", {})
    temporal = digest.get("temporal_hints", {})

    lines = [
        f"File: {classification.get('name', 'unknown')}",
        f"Type: {classification.get('category', 'unknown')} ({classification.get('mime_type', '')})",
        f"Size: {classification.get('size', 0):,} bytes",
        f"Status: {digest.get('status', 'unknown')}",
    ]

    if temporal.get("timestamp"):
        lines.append(f"Date: {temporal['timestamp']} ({temporal.get('confidence', 'unknown')} confidence via {temporal.get('source', 'unknown')})")

    lines.append(f"Estimated tokens: {digest.get('token_estimate', 0):,}")

    # Add type-specific info
    if "page_count" in metadata:
        lines.append(f"Pages: {metadata['page_count']}")
    if "width" in metadata and "height" in metadata:
        lines.append(f"Dimensions: {metadata['width']}x{metadata['height']}")
    if "line_count" in metadata:
        lines.append(f"Lines: {metadata['line_count']}")

    return "\n".join(lines)


# Tool definitions for LLM
DIGEST_TOOLS = [
    {
        "name": "generate_file_digest",
        "description": "Generate a digest (metadata summary) for a file. This extracts type info, metadata, temporal hints, and token estimates without full AI processing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "get_file_content_for_processing",
        "description": "Get the prepared content for a file, ready for AI processing. For large files, this returns summarized/truncated content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file"
                }
            },
            "required": ["file_path"]
        }
    }
]


def _generate_digest_tool(file_path: str) -> str:
    """Tool wrapper for generate_digest."""
    digest = generate_digest(file_path)
    return json.dumps(digest, indent=2)


def _get_content_tool(file_path: str) -> str:
    """Tool wrapper for get_content_for_ai."""
    return get_content_for_ai(file_path)


DIGEST_HANDLERS = {
    "generate_file_digest": _generate_digest_tool,
    "get_file_content_for_processing": _get_content_tool,
}


# Test
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        path = sys.argv[1]
        print("=== Digest Summary ===")
        print(get_digest_summary(path))
        print("\n=== Full Digest ===")
        digest = generate_digest(path)
        print(json.dumps(digest, indent=2))
    else:
        print("Usage: python digest.py <file_path>")
