"""
Archive extraction for batch ingestion.

Supports extracting files from:
- ZIP (Python stdlib)
- TAR, TAR.GZ, TAR.BZ2, TAR.XZ (Python stdlib)
- 7z (py7zr library - optional)
- RAR (rarfile library - optional)
"""

import os
import tempfile
import hashlib
from pathlib import Path
from typing import Generator
from contextlib import contextmanager

from .content_types import get_content_type, ARCHIVE_EXTENSIONS

# Optional imports for additional archive formats
try:
    import py7zr
    HAS_7Z = True
except ImportError:
    HAS_7Z = False

try:
    import rarfile
    HAS_RAR = True
except ImportError:
    HAS_RAR = False


def get_archive_type(file_path: Path | str) -> str | None:
    """
    Determine archive type from file extension.

    Returns:
        'zip', 'tar', '7z', 'rar', or None
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    ext = file_path.suffix.lower().lstrip('.')
    name_lower = file_path.name.lower()

    # Check for compound extensions
    if name_lower.endswith('.tar.gz') or name_lower.endswith('.tgz'):
        return 'tar'
    if name_lower.endswith('.tar.bz2'):
        return 'tar'
    if name_lower.endswith('.tar.xz'):
        return 'tar'

    if ext == 'zip':
        return 'zip'
    if ext in ('tar', 'gz', 'bz2', 'xz', 'tgz'):
        return 'tar'
    if ext == '7z':
        return '7z'
    if ext == 'rar':
        return 'rar'

    return None


def get_tar_mode(file_path: Path) -> str:
    """Get tarfile open mode based on compression."""
    name_lower = file_path.name.lower()

    if name_lower.endswith('.tar.gz') or name_lower.endswith('.tgz'):
        return 'r:gz'
    if name_lower.endswith('.tar.bz2'):
        return 'r:bz2'
    if name_lower.endswith('.tar.xz'):
        return 'r:xz'
    if name_lower.endswith('.tar'):
        return 'r:'

    # Try to detect from extension
    ext = file_path.suffix.lower()
    if ext == '.gz':
        return 'r:gz'
    if ext == '.bz2':
        return 'r:bz2'
    if ext == '.xz':
        return 'r:xz'

    return 'r:*'  # Auto-detect


def scan_archive_contents(
    archive_path: Path | str,
    types: set[str] | None = None
) -> list[dict]:
    """
    List files inside archive matching content types (without extracting).

    Args:
        archive_path: Path to the archive file
        types: Set of content types to match, or None for all files

    Returns:
        List of dicts with 'internal_path', 'size', 'content_type' for each matching file
    """
    if isinstance(archive_path, str):
        archive_path = Path(archive_path)

    archive_type = get_archive_type(archive_path)
    if not archive_type:
        return []

    results = []

    try:
        if archive_type == 'zip':
            results = _scan_zip(archive_path, types)
        elif archive_type == 'tar':
            results = _scan_tar(archive_path, types)
        elif archive_type == '7z':
            results = _scan_7z(archive_path, types)
        elif archive_type == 'rar':
            results = _scan_rar(archive_path, types)
    except Exception as e:
        print(f"Warning: Could not scan archive {archive_path}: {e}")

    return results


def _scan_zip(archive_path: Path, types: set[str] | None) -> list[dict]:
    """Scan ZIP archive contents."""
    import zipfile

    results = []
    with zipfile.ZipFile(archive_path, 'r') as zf:
        for info in zf.infolist():
            # Skip directories
            if info.is_dir():
                continue

            internal_path = info.filename
            content_type = get_content_type(internal_path)

            # Filter by type if specified
            if types and content_type not in types:
                continue

            results.append({
                'internal_path': internal_path,
                'size': info.file_size,
                'content_type': content_type,
            })

    return results


def _scan_tar(archive_path: Path, types: set[str] | None) -> list[dict]:
    """Scan TAR archive contents."""
    import tarfile

    results = []
    mode = get_tar_mode(archive_path)

    with tarfile.open(archive_path, mode) as tf:
        for member in tf.getmembers():
            # Skip directories
            if not member.isfile():
                continue

            internal_path = member.name
            content_type = get_content_type(internal_path)

            # Filter by type if specified
            if types and content_type not in types:
                continue

            results.append({
                'internal_path': internal_path,
                'size': member.size,
                'content_type': content_type,
            })

    return results


def _scan_7z(archive_path: Path, types: set[str] | None) -> list[dict]:
    """Scan 7z archive contents."""
    if not HAS_7Z:
        print(f"Warning: py7zr not installed, cannot scan {archive_path}")
        return []

    results = []
    with py7zr.SevenZipFile(archive_path, 'r') as szf:
        for name, info in szf.archiveinfo().files.items():
            # Skip directories
            if info.is_directory:
                continue

            content_type = get_content_type(name)

            # Filter by type if specified
            if types and content_type not in types:
                continue

            results.append({
                'internal_path': name,
                'size': info.uncompressed,
                'content_type': content_type,
            })

    return results


def _scan_rar(archive_path: Path, types: set[str] | None) -> list[dict]:
    """Scan RAR archive contents."""
    if not HAS_RAR:
        print(f"Warning: rarfile not installed, cannot scan {archive_path}")
        return []

    results = []
    with rarfile.RarFile(archive_path, 'r') as rf:
        for info in rf.infolist():
            # Skip directories
            if info.is_dir():
                continue

            internal_path = info.filename
            content_type = get_content_type(internal_path)

            # Filter by type if specified
            if types and content_type not in types:
                continue

            results.append({
                'internal_path': internal_path,
                'size': info.file_size,
                'content_type': content_type,
            })

    return results


@contextmanager
def extract_matching_files(
    archive_path: Path | str,
    types: set[str] | None = None,
    temp_dir: Path | str | None = None
) -> Generator[list[tuple[Path, str]], None, None]:
    """
    Extract files matching content types to a temporary directory.

    Context manager that yields extracted files and cleans up on exit.

    Args:
        archive_path: Path to the archive file
        types: Set of content types to match, or None for all files
        temp_dir: Optional base temp directory, creates subdirectory inside

    Yields:
        List of (extracted_path, internal_path) tuples
    """
    if isinstance(archive_path, str):
        archive_path = Path(archive_path)

    archive_type = get_archive_type(archive_path)
    if not archive_type:
        yield []
        return

    # Create temp directory for extraction
    base_temp = Path(temp_dir) if temp_dir else None
    extract_dir = tempfile.mkdtemp(
        prefix='euno_extract_',
        dir=base_temp
    )
    extract_path = Path(extract_dir)

    try:
        extracted = []

        if archive_type == 'zip':
            extracted = _extract_zip(archive_path, types, extract_path)
        elif archive_type == 'tar':
            extracted = _extract_tar(archive_path, types, extract_path)
        elif archive_type == '7z':
            extracted = _extract_7z(archive_path, types, extract_path)
        elif archive_type == 'rar':
            extracted = _extract_rar(archive_path, types, extract_path)

        yield extracted

    finally:
        # Cleanup temp directory
        import shutil
        if extract_path.exists():
            shutil.rmtree(extract_path, ignore_errors=True)


def _extract_zip(
    archive_path: Path,
    types: set[str] | None,
    extract_path: Path
) -> list[tuple[Path, str]]:
    """Extract matching files from ZIP archive."""
    import zipfile

    results = []
    with zipfile.ZipFile(archive_path, 'r') as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue

            internal_path = info.filename
            content_type = get_content_type(internal_path)

            if types and content_type not in types:
                continue

            # Extract file
            extracted = zf.extract(info, extract_path)
            results.append((Path(extracted), internal_path))

    return results


def _extract_tar(
    archive_path: Path,
    types: set[str] | None,
    extract_path: Path
) -> list[tuple[Path, str]]:
    """Extract matching files from TAR archive."""
    import tarfile

    results = []
    mode = get_tar_mode(archive_path)

    with tarfile.open(archive_path, mode) as tf:
        for member in tf.getmembers():
            if not member.isfile():
                continue

            internal_path = member.name
            content_type = get_content_type(internal_path)

            if types and content_type not in types:
                continue

            # Security: prevent path traversal
            if internal_path.startswith('/') or '..' in internal_path:
                continue

            # Extract file
            tf.extract(member, extract_path)
            results.append((extract_path / internal_path, internal_path))

    return results


def _extract_7z(
    archive_path: Path,
    types: set[str] | None,
    extract_path: Path
) -> list[tuple[Path, str]]:
    """Extract matching files from 7z archive."""
    if not HAS_7Z:
        print(f"Warning: py7zr not installed, cannot extract {archive_path}")
        return []

    results = []

    # Get list of files to extract
    files_to_extract = []
    with py7zr.SevenZipFile(archive_path, 'r') as szf:
        for name in szf.getnames():
            content_type = get_content_type(name)
            if types and content_type not in types:
                continue
            files_to_extract.append(name)

    # Extract selected files
    if files_to_extract:
        with py7zr.SevenZipFile(archive_path, 'r') as szf:
            szf.extract(extract_path, targets=files_to_extract)

        for internal_path in files_to_extract:
            extracted_path = extract_path / internal_path
            if extracted_path.exists() and extracted_path.is_file():
                results.append((extracted_path, internal_path))

    return results


def _extract_rar(
    archive_path: Path,
    types: set[str] | None,
    extract_path: Path
) -> list[tuple[Path, str]]:
    """Extract matching files from RAR archive."""
    if not HAS_RAR:
        print(f"Warning: rarfile not installed, cannot extract {archive_path}")
        return []

    results = []
    with rarfile.RarFile(archive_path, 'r') as rf:
        for info in rf.infolist():
            if info.is_dir():
                continue

            internal_path = info.filename
            content_type = get_content_type(internal_path)

            if types and content_type not in types:
                continue

            # Extract file
            rf.extract(info, extract_path)
            results.append((extract_path / internal_path, internal_path))

    return results


def get_archive_manifest_key(
    archive_rel_path: str,
    internal_path: str
) -> str:
    """
    Generate unique manifest key for a file inside an archive.

    Format: "archive_path::internal_path"

    Args:
        archive_rel_path: Relative path to the archive from source directory
        internal_path: Path inside the archive

    Returns:
        Unique key like "data/archive.zip::docs/readme.md"
    """
    return f"{archive_rel_path}::{internal_path}"


def parse_archive_manifest_key(key: str) -> tuple[str, str] | None:
    """
    Parse an archive manifest key.

    Args:
        key: Manifest key like "data/archive.zip::docs/readme.md"

    Returns:
        Tuple of (archive_path, internal_path) or None if not an archive key
    """
    if '::' not in key:
        return None

    parts = key.split('::', 1)
    if len(parts) != 2:
        return None

    return (parts[0], parts[1])


def compute_archive_content_hash(
    archive_path: Path | str,
    internal_path: str
) -> str | None:
    """
    Compute hash of a specific file inside an archive without extracting.

    Args:
        archive_path: Path to the archive
        internal_path: Path inside the archive

    Returns:
        SHA256 hash or None if file not found
    """
    if isinstance(archive_path, str):
        archive_path = Path(archive_path)

    archive_type = get_archive_type(archive_path)
    if not archive_type:
        return None

    try:
        if archive_type == 'zip':
            return _hash_zip_member(archive_path, internal_path)
        elif archive_type == 'tar':
            return _hash_tar_member(archive_path, internal_path)
        # For 7z and RAR, we'd need to extract to hash
        # Skip for now - use archive hash + internal path as identifier
    except Exception:
        pass

    return None


def _hash_zip_member(archive_path: Path, internal_path: str) -> str | None:
    """Hash a file inside a ZIP without full extraction."""
    import zipfile

    with zipfile.ZipFile(archive_path, 'r') as zf:
        try:
            with zf.open(internal_path) as f:
                hasher = hashlib.sha256()
                for chunk in iter(lambda: f.read(65536), b''):
                    hasher.update(chunk)
                return hasher.hexdigest()
        except KeyError:
            return None


def _hash_tar_member(archive_path: Path, internal_path: str) -> str | None:
    """Hash a file inside a TAR without full extraction."""
    import tarfile

    mode = get_tar_mode(archive_path)
    with tarfile.open(archive_path, mode) as tf:
        try:
            member = tf.getmember(internal_path)
            if not member.isfile():
                return None
            f = tf.extractfile(member)
            if f is None:
                return None
            hasher = hashlib.sha256()
            for chunk in iter(lambda: f.read(65536), b''):
                hasher.update(chunk)
            return hasher.hexdigest()
        except KeyError:
            return None


def is_archive_supported(file_path: Path | str) -> bool:
    """Check if archive format is supported (library available)."""
    archive_type = get_archive_type(file_path)

    if archive_type in ('zip', 'tar'):
        return True
    if archive_type == '7z':
        return HAS_7Z
    if archive_type == 'rar':
        return HAS_RAR

    return False


def get_unsupported_reason(file_path: Path | str) -> str | None:
    """Get reason why an archive is not supported."""
    archive_type = get_archive_type(file_path)

    if archive_type == '7z' and not HAS_7Z:
        return "py7zr library not installed (pip install py7zr)"
    if archive_type == 'rar' and not HAS_RAR:
        return "rarfile library not installed (pip install rarfile)"

    return None
