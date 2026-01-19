"""
Deduplication - Track processed files to avoid reprocessing.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


DATA_DIR = Path(__file__).parent.parent.parent / "data"
MANIFEST_PATH = DATA_DIR / "system" / "store" / "processed.jsonl"


def compute_hash(content: str) -> str:
    """Compute SHA-256 hash of content.

    Args:
        content: File content as string

    Returns:
        Hex digest of SHA-256 hash
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def _ensure_manifest_dir():
    """Ensure the manifest directory exists."""
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_manifest() -> dict:
    """Load the processing manifest.

    Returns:
        Dict mapping content hash to processing info
    """
    if not MANIFEST_PATH.exists():
        return {}

    manifest = {}
    try:
        with open(MANIFEST_PATH, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        manifest[entry['hash']] = entry
                    except (json.JSONDecodeError, KeyError):
                        continue
    except Exception:
        return {}

    return manifest


def is_duplicate(content: str) -> bool:
    """Check if content has already been processed.

    Args:
        content: File content to check

    Returns:
        True if already processed, False otherwise
    """
    content_hash = compute_hash(content)
    manifest = _load_manifest()
    return content_hash in manifest


def get_processed_info(content: str) -> Optional[dict]:
    """Get processing info for content if it was processed before.

    Args:
        content: File content to check

    Returns:
        Processing info dict or None if not processed
    """
    content_hash = compute_hash(content)
    manifest = _load_manifest()
    return manifest.get(content_hash)


def record_processed(
    path: str,
    content: str,
    date: str,
    date_source: str
) -> None:
    """Record that a file has been processed.

    Args:
        path: Original file path
        content: File content (used for hash)
        date: Date extracted for the file
        date_source: How the date was determined
    """
    _ensure_manifest_dir()

    content_hash = compute_hash(content)
    entry = {
        "hash": content_hash,
        "path": path,
        "date": date,
        "date_source": date_source,
        "processed_at": datetime.now().isoformat()
    }

    # Append to manifest
    with open(MANIFEST_PATH, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def clear_manifest() -> int:
    """Clear the processing manifest.

    Returns:
        Number of entries cleared
    """
    if not MANIFEST_PATH.exists():
        return 0

    manifest = _load_manifest()
    count = len(manifest)

    MANIFEST_PATH.unlink()

    return count
