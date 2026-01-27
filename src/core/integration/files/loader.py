"""
File Loader - Load files into RLM-friendly format for processing.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


# Size limits
MAX_FILE_SIZE = 500 * 1024  # 500KB max file size
MAX_CONTENT_SIZE = 50 * 1024  # 50KB max content for RLM

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    '.txt', '.md', '.markdown',
    '.json', '.yaml', '.yml',
    '.csv', '.tsv',
    '.log',
    '.rst', '.org',
    '.html', '.htm', '.xml',
}


@dataclass
class FileItem:
    """A loaded file ready for RLM processing."""
    path: str  # Absolute path
    name: str  # Filename
    content: str  # File content (may be truncated)
    size: int  # Original file size in bytes
    mtime: float  # Modification timestamp
    extension: str  # File extension (lowercase, with dot)
    truncated: bool = False  # Whether content was truncated


def _is_supported_file(path: Path) -> bool:
    """Check if file extension is supported."""
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def _load_file_content(path: Path) -> tuple[str, bool]:
    """Load file content, truncating if necessary.

    Returns:
        (content, was_truncated)
    """
    try:
        content = path.read_text(encoding='utf-8')
        if len(content) > MAX_CONTENT_SIZE:
            return content[:MAX_CONTENT_SIZE], True
        return content, False
    except UnicodeDecodeError:
        # Try with latin-1 as fallback
        try:
            content = path.read_text(encoding='latin-1')
            if len(content) > MAX_CONTENT_SIZE:
                return content[:MAX_CONTENT_SIZE], True
            return content, False
        except Exception:
            return "", False


def load_files(path: Path, recursive: bool = True) -> dict:
    """Load files from a path into RLM-friendly format.

    Args:
        path: File or directory path
        recursive: Whether to search directories recursively

    Returns:
        {
            "items": [FileItem, ...],
            "metadata": {
                "total_files": int,
                "total_chars": int,
                "extensions": {"ext": count, ...},
                "skipped": {"too_large": [...], "unsupported": [...], "unreadable": [...]}
            }
        }
    """
    items: List[FileItem] = []
    skipped = {
        "too_large": [],
        "unsupported": [],
        "unreadable": []
    }
    extensions: dict[str, int] = {}

    # Normalize path
    path = Path(path).expanduser().resolve()

    if not path.exists():
        return {
            "items": [],
            "metadata": {
                "total_files": 0,
                "total_chars": 0,
                "extensions": {},
                "skipped": skipped,
                "error": f"Path does not exist: {path}"
            }
        }

    # Collect files to process
    if path.is_file():
        files_to_process = [path]
    else:
        if recursive:
            files_to_process = [f for f in path.rglob("*") if f.is_file()]
        else:
            files_to_process = [f for f in path.iterdir() if f.is_file()]

    # Process each file
    for file_path in sorted(files_to_process):
        # Check extension
        if not _is_supported_file(file_path):
            skipped["unsupported"].append(str(file_path))
            continue

        # Check size
        try:
            stat = file_path.stat()
            if stat.st_size > MAX_FILE_SIZE:
                skipped["too_large"].append(str(file_path))
                continue

            # Load content
            content, truncated = _load_file_content(file_path)

            if not content:
                skipped["unreadable"].append(str(file_path))
                continue

            ext = file_path.suffix.lower()
            extensions[ext] = extensions.get(ext, 0) + 1

            items.append(FileItem(
                path=str(file_path),
                name=file_path.name,
                content=content,
                size=stat.st_size,
                mtime=stat.st_mtime,
                extension=ext,
                truncated=truncated
            ))

        except Exception as e:
            skipped["unreadable"].append(f"{file_path}: {e}")

    # Calculate total characters
    total_chars = sum(len(item.content) for item in items)

    return {
        "items": items,
        "metadata": {
            "total_files": len(items),
            "total_chars": total_chars,
            "extensions": extensions,
            "skipped": skipped
        }
    }


def files_to_rlm_format(items: List[FileItem]) -> dict:
    """Convert FileItems to format expected by RLM REPL.

    Args:
        items: List of FileItem objects

    Returns:
        Dict with items as plain dicts and metadata
    """
    return {
        "items": [
            {
                "path": item.path,
                "name": item.name,
                "content": item.content,
                "size": item.size,
                "mtime": item.mtime,
                "extension": item.extension
            }
            for item in items
        ],
        "metadata": {
            "total_files": len(items),
            "total_chars": sum(len(item.content) for item in items),
            "extensions": list(set(item.extension for item in items))
        }
    }
