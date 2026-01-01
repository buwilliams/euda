"""
Content type detection and filtering for batch ingestion.

Provides extension-based classification into content types:
- text: documents, code, data files
- images: photos, graphics
- video: video files
- audio: music, audio files
"""

from pathlib import Path

# Extension mappings (based on /mnt/d/Lifelog/count.sh)

TEXT_EXTENSIONS = {
    # Documents
    'txt', 'md', 'markdown', 'rst', 'org', 'adoc', 'asciidoc', 'rtf', 'log',
    # Data formats
    'csv', 'tsv', 'json', 'jsonl', 'ndjson', 'xml', 'yaml', 'yml', 'toml',
    'ini', 'cfg', 'conf', 'env', 'properties', 'sql', 'tex', 'bib',
    # Email
    'mbox', 'eml', 'msg', 'pst', 'ost',
    # Web
    'html', 'htm', 'xhtml', 'css', 'svg',
    # Code - C/C++
    'c', 'h', 'cc', 'hh', 'cpp', 'hpp', 'cxx', 'hxx',
    # Code - JVM
    'java', 'kt', 'kts', 'scala', 'groovy',
    # Code - Python
    'py', 'pyw', 'ipynb',
    # Code - JavaScript/TypeScript
    'js', 'jsx', 'ts', 'tsx', 'mjs', 'cjs',
    # Code - Systems
    'go', 'rs', 'swift',
    # Code - Scripting
    'rb', 'php', 'pl', 'pm', 'r', 'jl', 'lua', 'dart',
    # Code - Shell
    'sh', 'bash', 'zsh', 'fish', 'ps1', 'bat', 'cmd',
    # Code - Build
    'make', 'makefile', 'mk', 'cmake', 'gradle',
    # Documents (binary but text-extractable)
    'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'odt', 'ods', 'odp', 'epub',
    # Other
    'ics', 'vcf', 'patch', 'diff', 'lock',
}

IMAGE_EXTENSIONS = {
    # Common formats
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tif', 'tiff',
    # Apple formats
    'heic', 'heif',
    # RAW formats
    'raw', 'cr2', 'nef', 'arw', 'dng', 'orf', 'rw2',
    # Other
    'svg', 'ico', 'avif',
}

VIDEO_EXTENSIONS = {
    # Common formats
    'mp4', 'm4v', 'mov', 'mkv', 'webm', 'avi', 'wmv', 'flv',
    # MPEG formats
    'mpg', 'mpeg', 'mpe',
    # Mobile formats
    '3gp', '3g2',
    # Broadcast formats
    'mts', 'm2ts', 'ts', 'vob',
    # Other
    'ogv',
}

AUDIO_EXTENSIONS = {
    # Common formats
    'mp3', 'wav', 'flac', 'aac', 'm4a', 'ogg', 'wma',
    # Lossless formats
    'aiff', 'alac', 'ape', 'wv',
    # Other
    'opus', 'mid', 'midi',
}

ARCHIVE_EXTENSIONS = {
    # Standard archives
    'zip', 'tar', 'gz', 'tgz', 'bz2', 'xz',
    # Proprietary archives
    '7z', 'rar',
}

# Map of content type -> extension set
CONTENT_TYPE_MAP = {
    'text': TEXT_EXTENSIONS,
    'images': IMAGE_EXTENSIONS,
    'video': VIDEO_EXTENSIONS,
    'audio': AUDIO_EXTENSIONS,
}

# All valid content types
VALID_CONTENT_TYPES = set(CONTENT_TYPE_MAP.keys())


def get_extension(file_path: Path | str) -> str:
    """Get lowercase extension without dot."""
    if isinstance(file_path, str):
        file_path = Path(file_path)

    ext = file_path.suffix.lower().lstrip('.')

    # Handle compound extensions like .tar.gz
    if ext in ('gz', 'bz2', 'xz'):
        stem_ext = Path(file_path.stem).suffix.lower().lstrip('.')
        if stem_ext == 'tar':
            return f'tar.{ext}' if ext != 'gz' else 'tgz'

    return ext


def get_content_type(file_path: Path | str) -> str | None:
    """
    Get content type for a file based on extension.

    Returns:
        'text', 'images', 'video', 'audio', or None if not recognized
    """
    ext = get_extension(file_path)

    for content_type, extensions in CONTENT_TYPE_MAP.items():
        if ext in extensions:
            return content_type

    return None


def matches_content_types(file_path: Path | str, types: set[str]) -> bool:
    """
    Check if a file matches any of the requested content types.

    Args:
        file_path: Path to the file
        types: Set of content types to match ('text', 'images', 'video', 'audio')
               If empty, matches all files

    Returns:
        True if file matches any of the requested types, or if types is empty
    """
    if not types:
        return True  # No filter = match all

    content_type = get_content_type(file_path)
    return content_type in types


def is_archive(file_path: Path | str) -> bool:
    """Check if file is a supported archive format."""
    ext = get_extension(file_path)
    return ext in ARCHIVE_EXTENSIONS


def parse_content_types(type_string: str) -> set[str]:
    """
    Parse a comma-separated content type string.

    Args:
        type_string: e.g., "text,images" or "video"

    Returns:
        Set of valid content types

    Raises:
        ValueError if invalid content type specified
    """
    if not type_string:
        return set()

    types = {t.strip().lower() for t in type_string.split(',')}

    invalid = types - VALID_CONTENT_TYPES
    if invalid:
        raise ValueError(
            f"Invalid content type(s): {', '.join(invalid)}. "
            f"Valid types are: {', '.join(sorted(VALID_CONTENT_TYPES))}"
        )

    return types


def get_all_extensions_for_types(types: set[str]) -> set[str]:
    """
    Get all file extensions for the given content types.

    Args:
        types: Set of content types

    Returns:
        Set of all extensions (lowercase, without dot)
    """
    extensions = set()
    for content_type in types:
        if content_type in CONTENT_TYPE_MAP:
            extensions.update(CONTENT_TYPE_MAP[content_type])
    return extensions
