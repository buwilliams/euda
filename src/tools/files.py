"""
File processing tools for the Ingestion Agent.

Handles extraction of content and metadata from various file types.
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path

# Base paths
DATA_DIR = Path(__file__).parent.parent.parent / "data"
INBOX_DIR = DATA_DIR / "inbox"
PENDING_DIR = INBOX_DIR / "pending"
PROCESSED_DIR = INBOX_DIR / "processed"
FAILED_DIR = INBOX_DIR / "failed"


def list_pending_files() -> str:
    """
    List all files in the inbox pending directory.

    Returns:
        List of pending files with their details
    """
    files = []
    for f in PENDING_DIR.iterdir():
        if f.is_file() and not f.name.startswith('.'):
            stat = f.stat()
            files.append({
                "name": f.name,
                "path": str(f),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })

    if not files:
        return "No pending files in inbox."

    result = "Pending files:\n"
    for f in files:
        result += f"- {f['name']} ({f['size']} bytes, modified: {f['modified']})\n"
    return result


def read_file_content(file_path: str) -> str:
    """
    Read content from a file, handling different file types.

    Args:
        file_path: Path to the file

    Returns:
        Extracted content as text, or error message
    """
    path = Path(file_path)

    if not path.exists():
        return f"Error: File not found: {file_path}"

    suffix = path.suffix.lower()

    # Text files
    if suffix in ['.txt', '.md', '.markdown', '.text']:
        return _read_text_file(path)

    # JSON files
    if suffix == '.json':
        return _read_json_file(path)

    # Images - return metadata and suggest description
    if suffix in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic']:
        return _read_image_file(path)

    # PDF files
    if suffix == '.pdf':
        return _read_pdf_file(path)

    # Try reading as text
    try:
        return _read_text_file(path)
    except Exception:
        return f"Unable to read file type: {suffix}. File: {path.name}"


def _read_text_file(path: Path) -> str:
    """Read a plain text file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"[Text file: {path.name}]\n\n{content}"
    except UnicodeDecodeError:
        with open(path, 'r', encoding='latin-1') as f:
            content = f.read()
        return f"[Text file: {path.name}]\n\n{content}"


def _read_json_file(path: Path) -> str:
    """Read and format a JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return f"[JSON file: {path.name}]\n\n{json.dumps(data, indent=2)}"


def _read_image_file(path: Path) -> str:
    """Extract metadata from an image file."""
    result = f"[Image file: {path.name}]\n\n"

    # Try to extract EXIF data
    exif_data = _extract_exif(path)
    if exif_data:
        result += "EXIF Metadata:\n"
        for key, value in exif_data.items():
            result += f"  {key}: {value}\n"
        result += "\n"

    result += "Note: This is an image file. Please describe what you see or provide context about this image."
    return result


def _extract_exif(path: Path) -> dict:
    """Extract EXIF data from an image if possible."""
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        img = Image.open(path)
        exif = img._getexif()

        if not exif:
            return {}

        exif_data = {}
        important_tags = ['DateTime', 'DateTimeOriginal', 'Make', 'Model',
                         'GPSInfo', 'ImageDescription', 'UserComment']

        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag in important_tags:
                exif_data[tag] = str(value)

        return exif_data
    except ImportError:
        return {"note": "Install Pillow for EXIF extraction: pip install Pillow"}
    except Exception as e:
        return {"error": str(e)}


def _read_pdf_file(path: Path) -> str:
    """Extract text from a PDF file."""
    try:
        import pypdf

        reader = pypdf.PdfReader(path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        return f"[PDF file: {path.name}]\n\n{text}"
    except ImportError:
        return f"[PDF file: {path.name}]\n\nNote: Install pypdf for PDF extraction: pip install pypdf"
    except Exception as e:
        return f"[PDF file: {path.name}]\n\nError reading PDF: {str(e)}"


def extract_temporal_hints(file_path: str) -> str:
    """
    Extract temporal hints from a file (filename, metadata, content).

    Args:
        file_path: Path to the file

    Returns:
        Temporal hints found in the file
    """
    path = Path(file_path)
    hints = []

    # Check filename for dates
    filename_hints = _extract_date_from_filename(path.name)
    if filename_hints:
        hints.append(f"Filename suggests: {filename_hints}")

    # Check file modification time
    stat = path.stat()
    mtime = datetime.fromtimestamp(stat.st_mtime)
    hints.append(f"File modified: {mtime.isoformat()}")

    # Check EXIF for images
    if path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.heic']:
        exif = _extract_exif(path)
        if 'DateTimeOriginal' in exif:
            hints.append(f"EXIF DateTimeOriginal: {exif['DateTimeOriginal']}")
        elif 'DateTime' in exif:
            hints.append(f"EXIF DateTime: {exif['DateTime']}")

    if not hints:
        return "No temporal hints found."

    return "Temporal hints:\n" + "\n".join(f"- {h}" for h in hints)


def _extract_date_from_filename(filename: str) -> str:
    """Try to extract a date from a filename."""
    import re

    # Common patterns
    patterns = [
        (r'(\d{4})-(\d{2})-(\d{2})', 'YYYY-MM-DD'),
        (r'(\d{4})(\d{2})(\d{2})', 'YYYYMMDD'),
        (r'(\d{2})-(\d{2})-(\d{4})', 'MM-DD-YYYY'),
        (r'IMG_(\d{4})(\d{2})(\d{2})', 'IMG_YYYYMMDD'),
        (r'Screenshot[_ ](\d{4})-(\d{2})-(\d{2})', 'Screenshot_YYYY-MM-DD'),
    ]

    for pattern, format_name in patterns:
        match = re.search(pattern, filename)
        if match:
            groups = match.groups()
            if format_name in ['YYYY-MM-DD', 'YYYYMMDD', 'IMG_YYYYMMDD', 'Screenshot_YYYY-MM-DD']:
                return f"{groups[0]}-{groups[1]}-{groups[2]}"
            elif format_name == 'MM-DD-YYYY':
                return f"{groups[2]}-{groups[0]}-{groups[1]}"

    return None


def mark_file_processed(file_path: str) -> str:
    """
    Move a file from pending to processed.

    Args:
        file_path: Path to the file

    Returns:
        Confirmation message
    """
    path = Path(file_path)

    if not path.exists():
        return f"Error: File not found: {file_path}"

    # Generate unique name if collision
    dest = PROCESSED_DIR / path.name
    if dest.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dest = PROCESSED_DIR / f"{path.stem}_{timestamp}{path.suffix}"

    shutil.move(str(path), str(dest))
    return f"File moved to processed: {dest.name}"


def mark_file_failed(file_path: str, reason: str = "") -> str:
    """
    Move a file from pending to failed.

    Args:
        file_path: Path to the file
        reason: Reason for failure

    Returns:
        Confirmation message
    """
    path = Path(file_path)

    if not path.exists():
        return f"Error: File not found: {file_path}"

    # Generate unique name if collision
    dest = FAILED_DIR / path.name
    if dest.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dest = FAILED_DIR / f"{path.stem}_{timestamp}{path.suffix}"

    shutil.move(str(path), str(dest))

    # Write failure reason
    if reason:
        reason_file = FAILED_DIR / f"{dest.stem}.reason.txt"
        with open(reason_file, 'w') as f:
            f.write(f"Failed: {datetime.now().isoformat()}\n")
            f.write(f"Reason: {reason}\n")

    return f"File moved to failed: {dest.name}"


# Tool definitions for the LLM
FILE_TOOLS = [
    {
        "name": "list_pending_files",
        "description": "List all files waiting to be processed in the inbox.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "read_file_content",
        "description": "Read and extract content from a file. Handles text, JSON, images (metadata), and PDFs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "extract_temporal_hints",
        "description": "Extract date/time hints from a file's name, metadata, and content.",
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
        "name": "mark_file_processed",
        "description": "Mark a file as successfully processed and move it to the processed folder.",
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
        "name": "mark_file_failed",
        "description": "Mark a file as failed to process and move it to the failed folder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for the failure"
                }
            },
            "required": ["file_path"]
        }
    }
]

# Tool handlers mapping
FILE_HANDLERS = {
    "list_pending_files": list_pending_files,
    "read_file_content": read_file_content,
    "extract_temporal_hints": extract_temporal_hints,
    "mark_file_processed": mark_file_processed,
    "mark_file_failed": mark_file_failed,
}


# Test
if __name__ == "__main__":
    print(list_pending_files())
