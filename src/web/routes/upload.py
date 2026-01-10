"""
Upload API Route

Handles file uploads by:
1. Saving the file to data/agents/user/uploads/{date}/
2. Adding full content to user's long-term memory (for text files)
3. Adding a brief entry to user's short-term memory
"""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, UploadFile, File

from ...tools.data.memory import add_memory, write_long_term_memory


router = APIRouter()

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
UPLOADS_DIR = DATA_DIR / "agents" / "user" / "uploads"

# File extensions we can read as text
TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".json", ".csv", ".tsv",
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
    ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".sh", ".bash", ".zsh", ".fish",
    ".sql", ".graphql",
    ".rs", ".go", ".java", ".kt", ".swift", ".c", ".cpp", ".h",
    ".rb", ".php", ".pl", ".lua", ".r", ".scala",
    ".log", ".env", ".gitignore", ".dockerignore",
}

# Max size for text content to include in long-term memory (100KB)
MAX_TEXT_SIZE = 100 * 1024


def is_text_file(filename: str) -> bool:
    """Check if file is a readable text file based on extension."""
    suffix = Path(filename).suffix.lower()
    return suffix in TEXT_EXTENSIONS


def get_upload_dir() -> Path:
    """Get today's upload directory, creating if needed."""
    today = datetime.now().strftime("%Y-%m-%d")
    upload_dir = UPLOADS_DIR / today
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def make_unique_filename(directory: Path, filename: str) -> str:
    """Generate a unique filename if one already exists."""
    path = directory / filename
    if not path.exists():
        return filename

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1

    while (directory / f"{stem}_{counter}{suffix}").exists():
        counter += 1

    return f"{stem}_{counter}{suffix}"


@router.post("")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file for processing.

    Saves the file and adds it to the user's memory:
    - Text files: full content stored in long-term memory
    - All files: brief entry added to short-term memory
    """
    today = datetime.now().strftime("%Y-%m-%d")
    upload_dir = get_upload_dir()

    # Save file with unique name if needed
    filename = make_unique_filename(upload_dir, file.filename)
    file_path = upload_dir / filename
    content_bytes = await file.read()
    file_path.write_bytes(content_bytes)

    # Determine file type and size
    file_size = len(content_bytes)
    file_size_str = f"{file_size / 1024:.1f}KB" if file_size >= 1024 else f"{file_size}B"
    is_text = is_text_file(filename)

    # For text files, add content to long-term memory
    if is_text and file_size <= MAX_TEXT_SIZE:
        try:
            text_content = content_bytes.decode("utf-8")
            memory_content = f"**Uploaded file:** {filename}\n\n```\n{text_content}\n```"
            write_long_term_memory(
                content=memory_content,
                agent_id="user",
                source="Upload"
            )
        except UnicodeDecodeError:
            # Not actually text, just note the upload
            write_long_term_memory(
                content=f"**Uploaded file:** {filename} ({file_size_str}) - binary file saved to uploads/{today}/",
                agent_id="user",
                source="Upload"
            )
    elif is_text and file_size > MAX_TEXT_SIZE:
        # Text file too large for memory, note location
        write_long_term_memory(
            content=f"**Uploaded file:** {filename} ({file_size_str}) - large text file saved to uploads/{today}/",
            agent_id="user",
            source="Upload"
        )
    else:
        # Binary file - just note the upload
        write_long_term_memory(
            content=f"**Uploaded file:** {filename} ({file_size_str}) - saved to uploads/{today}/",
            agent_id="user",
            source="Upload"
        )

    # Add brief entry to short-term memory
    add_memory(
        short_description=f"Uploaded {filename}",
        type="thing",
        agent_id="user"
    )

    return {
        "status": "uploaded",
        "filename": filename,
        "path": f"uploads/{today}/{filename}",
        "size": file_size_str,
        "message": "File saved and added to memory."
    }
