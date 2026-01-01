"""
Content Hash Utilities

Provides hash-based change detection for agent input directories.
Agents can use these utilities to avoid unnecessary work when their
input data hasn't changed.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


def compute_file_hash(file_path: Path) -> str:
    """
    Compute MD5 hash of a single file's content.

    Args:
        file_path: Path to the file

    Returns:
        Hex digest of file content hash
    """
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()


def compute_directory_hash(
    directory: Path,
    pattern: str = "*.md",
    exclude_prefix: str = "_"
) -> str:
    """
    Compute hash of all matching files in a directory.

    Files are sorted by name to ensure consistent hash.
    Hidden files and files starting with exclude_prefix are skipped.

    Args:
        directory: Directory to hash
        pattern: Glob pattern for files to include
        exclude_prefix: Skip files starting with this prefix

    Returns:
        Hex digest of combined content hash
    """
    if not directory.exists():
        return ""

    hasher = hashlib.md5()

    for file_path in sorted(directory.glob(pattern)):
        if file_path.name.startswith('.'):
            continue
        if exclude_prefix and file_path.name.startswith(exclude_prefix):
            continue

        with open(file_path, 'rb') as f:
            hasher.update(f.read())

    return hasher.hexdigest()


def compute_multi_directory_hash(
    directories: list[Path],
    pattern: str = "*.md",
    exclude_prefix: str = "_"
) -> str:
    """
    Compute combined hash across multiple directories.

    Args:
        directories: List of directories to hash
        pattern: Glob pattern for files to include
        exclude_prefix: Skip files starting with this prefix

    Returns:
        Hex digest of combined content hash
    """
    hasher = hashlib.md5()

    for directory in sorted(directories, key=str):
        if not directory.exists():
            continue

        for file_path in sorted(directory.glob(pattern)):
            if file_path.name.startswith('.'):
                continue
            if exclude_prefix and file_path.name.startswith(exclude_prefix):
                continue

            with open(file_path, 'rb') as f:
                hasher.update(f.read())

    return hasher.hexdigest()


def compute_files_hash(files: list[Path]) -> str:
    """
    Compute combined hash of specific files.

    Args:
        files: List of file paths to hash

    Returns:
        Hex digest of combined content hash
    """
    hasher = hashlib.md5()

    for file_path in sorted(files, key=str):
        if not file_path.exists():
            continue
        with open(file_path, 'rb') as f:
            hasher.update(f.read())

    return hasher.hexdigest()


def load_cached_hash(hash_file: Path) -> Optional[str]:
    """
    Load previously cached hash from file.

    Args:
        hash_file: Path to hash cache file

    Returns:
        Cached hash string or None if not found
    """
    if not hash_file.exists():
        return None

    try:
        content = hash_file.read_text().strip()
        # Handle both plain hash and JSON format
        if content.startswith('{'):
            data = json.loads(content)
            return data.get('hash')
        return content
    except (json.JSONDecodeError, IOError):
        return None


def save_cached_hash(hash_file: Path, content_hash: str, metadata: Optional[dict] = None):
    """
    Save hash to cache file.

    Args:
        hash_file: Path to save hash to
        content_hash: Hash string to save
        metadata: Optional metadata to include (saves as JSON)
    """
    hash_file.parent.mkdir(parents=True, exist_ok=True)

    if metadata:
        data = {
            'hash': content_hash,
            'computed_at': datetime.now().isoformat(),
            **metadata
        }
        hash_file.write_text(json.dumps(data, indent=2))
    else:
        hash_file.write_text(content_hash)


def has_content_changed(
    directory: Path,
    hash_file: Path,
    pattern: str = "*.md",
    exclude_prefix: str = "_"
) -> bool:
    """
    Check if directory content has changed since last hash.

    Args:
        directory: Directory to check
        hash_file: Path to cached hash file
        pattern: Glob pattern for files to include
        exclude_prefix: Skip files starting with this prefix

    Returns:
        True if content changed or no cached hash exists
    """
    cached_hash = load_cached_hash(hash_file)
    if cached_hash is None:
        return True

    current_hash = compute_directory_hash(directory, pattern, exclude_prefix)
    return current_hash != cached_hash


def has_files_changed(files: list[Path], hash_file: Path) -> bool:
    """
    Check if specific files have changed since last hash.

    Args:
        files: List of file paths to check
        hash_file: Path to cached hash file

    Returns:
        True if content changed or no cached hash exists
    """
    cached_hash = load_cached_hash(hash_file)
    if cached_hash is None:
        return True

    current_hash = compute_files_hash(files)
    return current_hash != cached_hash


def update_hash_if_changed(
    directory: Path,
    hash_file: Path,
    pattern: str = "*.md",
    exclude_prefix: str = "_"
) -> tuple[bool, str]:
    """
    Check if content changed and update hash if so.

    Convenience function that combines check and save.

    Args:
        directory: Directory to check
        hash_file: Path to hash cache file
        pattern: Glob pattern for files
        exclude_prefix: Skip files starting with this

    Returns:
        Tuple of (changed: bool, current_hash: str)
    """
    current_hash = compute_directory_hash(directory, pattern, exclude_prefix)
    cached_hash = load_cached_hash(hash_file)

    changed = cached_hash is None or current_hash != cached_hash

    if changed:
        save_cached_hash(hash_file, current_hash)

    return changed, current_hash
