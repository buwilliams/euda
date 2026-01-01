"""
File Classifier for Archivist Agent.

Detects file types using magic bytes (not just extensions) and determines
how files should be processed. Also handles ignore patterns for system files.
"""

import fnmatch
import hashlib
import json
import os
from pathlib import Path
from typing import Optional, Tuple

# Try to import python-magic, fall back to extension-based detection
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

# Data paths - Archivist agent directory
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
ARCHIVIST_DIR = DATA_DIR / "archivist"
CONFIG_FILE = ARCHIVIST_DIR / "config" / "config.json"
HASHES_FILE = ARCHIVIST_DIR / "config" / "processed_hashes.json"

# MIME type to handler category mapping
MIME_TO_CATEGORY = {
    # Images
    "image/jpeg": "image",
    "image/png": "image",
    "image/gif": "image",
    "image/webp": "image",
    "image/heic": "image",
    "image/heif": "image",
    "image/tiff": "image",
    "image/bmp": "image",

    # PDFs
    "application/pdf": "pdf",

    # Text
    "text/plain": "text",
    "text/markdown": "text",
    "text/html": "text",
    "text/css": "text",
    "text/csv": "text",
    "text/xml": "text",
    "application/json": "text",
    "application/xml": "text",
    "application/javascript": "text",

    # Audio
    "audio/mpeg": "audio",
    "audio/mp3": "audio",
    "audio/wav": "audio",
    "audio/x-wav": "audio",
    "audio/ogg": "audio",
    "audio/flac": "audio",
    "audio/aac": "audio",
    "audio/m4a": "audio",
    "audio/x-m4a": "audio",

    # Video
    "video/mp4": "video",
    "video/mpeg": "video",
    "video/quicktime": "video",
    "video/x-msvideo": "video",
    "video/webm": "video",
    "video/x-matroska": "video",

    # Archives
    "application/zip": "archive",
    "application/x-zip-compressed": "archive",
    "application/x-tar": "archive",
    "application/gzip": "archive",
    "application/x-gzip": "archive",
    "application/x-bzip2": "archive",
    "application/x-7z-compressed": "archive",
    "application/x-rar-compressed": "archive",

    # Email
    "application/mbox": "mbox",
    "message/rfc822": "mbox",
}

# Extension fallbacks when magic detection isn't available
EXTENSION_TO_CATEGORY = {
    # Images
    ".jpg": "image", ".jpeg": "image", ".png": "image", ".gif": "image",
    ".webp": "image", ".heic": "image", ".heif": "image", ".tiff": "image",
    ".tif": "image", ".bmp": "image",

    # PDFs
    ".pdf": "pdf",

    # Text
    ".txt": "text", ".md": "text", ".markdown": "text", ".html": "text",
    ".htm": "text", ".css": "text", ".csv": "text", ".xml": "text",
    ".json": "text", ".js": "text", ".py": "text", ".sh": "text",
    ".yaml": "text", ".yml": "text", ".ini": "text", ".cfg": "text",
    ".log": "text", ".rst": "text",

    # Audio
    ".mp3": "audio", ".wav": "audio", ".ogg": "audio", ".flac": "audio",
    ".aac": "audio", ".m4a": "audio", ".wma": "audio",

    # Video
    ".mp4": "video", ".mov": "video", ".avi": "video", ".mkv": "video",
    ".webm": "video", ".mpeg": "video", ".mpg": "video", ".wmv": "video",

    # Archives
    ".zip": "archive", ".tar": "archive", ".gz": "archive", ".tgz": "archive",
    ".bz2": "archive", ".7z": "archive", ".rar": "archive",

    # Email
    ".mbox": "mbox", ".eml": "mbox",
}

# Default ignore patterns
DEFAULT_IGNORE_PATTERNS = [
    ".DS_Store",
    "Thumbs.db",
    ".git",
    "__pycache__",
    "*.pyc",
    ".env",
    "node_modules",
    ".cache",
    "*.tmp",
    "*.temp",
    "*.swp",
    "*~",
    ".gitignore",
    ".dockerignore",
    "*.log",
]


def _load_config() -> dict:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


def _load_processed_hashes() -> dict:
    """Load the set of already-processed file hashes."""
    if HASHES_FILE.exists():
        with open(HASHES_FILE, 'r') as f:
            return json.load(f)
    return {}


def _save_processed_hash(file_hash: str, file_path: str):
    """Save a hash to the processed hashes file."""
    from datetime import date
    hashes = _load_processed_hashes()
    hashes[file_hash] = {
        "processed_at": date.today().isoformat(),
        "original_path": str(file_path)
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(HASHES_FILE, 'w') as f:
        json.dump(hashes, f, indent=2)


def compute_file_hash(file_path: str, chunk_size: int = 65536) -> str:
    """
    Compute SHA256 hash of a file.

    Uses chunked reading to handle large files without loading into memory.
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()


def is_duplicate(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a file has already been processed.

    Returns:
        Tuple of (is_duplicate, file_hash)
    """
    file_hash = compute_file_hash(file_path)
    processed = _load_processed_hashes()
    return file_hash in processed, file_hash


def mark_as_processed(file_path: str, file_hash: Optional[str] = None):
    """Mark a file as processed by saving its hash."""
    if file_hash is None:
        file_hash = compute_file_hash(file_path)
    _save_processed_hash(file_hash, file_path)


def detect_mime_type(file_path: str) -> Tuple[str, str]:
    """
    Detect MIME type of a file.

    Uses python-magic if available, falls back to extension-based detection.

    Returns:
        Tuple of (mime_type, detection_method)
    """
    path = Path(file_path)

    if HAS_MAGIC:
        try:
            mime = magic.Magic(mime=True)
            mime_type = mime.from_file(str(path))
            return mime_type, "magic"
        except Exception:
            pass

    # Fall back to extension-based detection
    ext = path.suffix.lower()
    for mime_type, category in MIME_TO_CATEGORY.items():
        if ext in EXTENSION_TO_CATEGORY and EXTENSION_TO_CATEGORY[ext] == category:
            return mime_type, "extension"

    return "application/octet-stream", "unknown"


def get_file_category(file_path: str) -> str:
    """
    Get the handler category for a file.

    Categories: image, pdf, text, audio, video, archive, mbox, unknown
    """
    mime_type, _ = detect_mime_type(file_path)

    # Check MIME type mapping
    if mime_type in MIME_TO_CATEGORY:
        return MIME_TO_CATEGORY[mime_type]

    # Fall back to extension
    ext = Path(file_path).suffix.lower()
    if ext in EXTENSION_TO_CATEGORY:
        return EXTENSION_TO_CATEGORY[ext]

    return "unknown"


def should_ignore(file_path: str) -> Tuple[bool, str]:
    """
    Check if a file should be ignored.

    Returns:
        Tuple of (should_ignore, reason)
    """
    path = Path(file_path)
    name = path.name

    # Load config for custom patterns
    config = _load_config()
    patterns = config.get("ignore_patterns", DEFAULT_IGNORE_PATTERNS)

    # Check against patterns
    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern):
            return True, f"matches pattern: {pattern}"
        if fnmatch.fnmatch(str(path), pattern):
            return True, f"matches pattern: {pattern}"

    # Check for hidden files
    if name.startswith('.') and name != '.':
        return True, "hidden file"

    # Check for empty files
    if path.exists() and path.stat().st_size == 0:
        return True, "empty file"

    return False, ""


def classify_file(file_path: str) -> dict:
    """
    Fully classify a file for ingestion processing.

    Returns a dict with:
        - path: original file path
        - name: file name
        - size: file size in bytes
        - mime_type: detected MIME type
        - detection_method: how MIME was detected (magic/extension/unknown)
        - category: handler category (image, pdf, text, etc.)
        - should_ignore: whether to skip this file
        - ignore_reason: why it should be ignored
        - is_duplicate: whether already processed
        - file_hash: SHA256 hash of content
    """
    path = Path(file_path)

    # Basic info
    result = {
        "path": str(path.absolute()),
        "name": path.name,
        "size": path.stat().st_size if path.exists() else 0,
    }

    # Check if should ignore first (cheap check)
    should_skip, ignore_reason = should_ignore(file_path)
    result["should_ignore"] = should_skip
    result["ignore_reason"] = ignore_reason

    if should_skip:
        result["mime_type"] = ""
        result["detection_method"] = ""
        result["category"] = ""
        result["is_duplicate"] = False
        result["file_hash"] = ""
        return result

    # Detect MIME type
    mime_type, detection_method = detect_mime_type(file_path)
    result["mime_type"] = mime_type
    result["detection_method"] = detection_method

    # Get category
    result["category"] = get_file_category(file_path)

    # Check for duplicates (more expensive - reads file)
    is_dup, file_hash = is_duplicate(file_path)
    result["is_duplicate"] = is_dup
    result["file_hash"] = file_hash

    return result


# Tool definitions for LLM
CLASSIFIER_TOOLS = [
    {
        "name": "classify_file",
        "description": "Classify a file to determine its type, category, and whether it should be processed. Returns MIME type, handler category (image/pdf/text/audio/video/archive/mbox), and checks for duplicates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to classify"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "check_duplicate",
        "description": "Check if a file has already been processed based on its content hash.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to check"
                }
            },
            "required": ["file_path"]
        }
    }
]


def _classify_file_tool(file_path: str) -> str:
    """Tool wrapper for classify_file."""
    result = classify_file(file_path)
    return json.dumps(result, indent=2)


def _check_duplicate_tool(file_path: str) -> str:
    """Tool wrapper for is_duplicate."""
    is_dup, file_hash = is_duplicate(file_path)
    if is_dup:
        return f"DUPLICATE: File with hash {file_hash[:16]}... has already been processed."
    return f"NEW: File hash {file_hash[:16]}... not seen before."


CLASSIFIER_HANDLERS = {
    "classify_file": _classify_file_tool,
    "check_duplicate": _check_duplicate_tool,
}


# Test
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        result = classify_file(sys.argv[1])
        print(json.dumps(result, indent=2))
    else:
        print(f"python-magic available: {HAS_MAGIC}")
        print("\nUsage: python classifier.py <file_path>")
