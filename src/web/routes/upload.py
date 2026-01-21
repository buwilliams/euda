"""
Upload API Route

Handles file uploads by:
1. Creating a job for the Chat agent to analyze the file
2. Saving the file as a job asset
3. Chat agent processes the job asynchronously using existing asset tools
"""

from pathlib import Path

from fastapi import APIRouter, UploadFile, File

from ...llms.tools.data.jobs import create_job, get_agent_inbox_job
from ...llms.tools.data.assets import write_asset_bytes
from ...llms.tools.data.memory import add_memory


router = APIRouter()

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


def is_text_file(filename: str) -> bool:
    """Check if file is a readable text file based on extension."""
    suffix = Path(filename).suffix.lower()
    return suffix in TEXT_EXTENSIONS


@router.post("")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file for processing.

    Creates a job with the file as an asset for Chat agent to analyze:
    - Text files: Chat will analyze for identity extraction
    - All files: stored as job assets
    """
    filename = file.filename
    content_bytes = await file.read()

    # Determine file type and size
    file_size = len(content_bytes)
    file_size_str = f"{file_size / 1024:.1f}KB" if file_size >= 1024 else f"{file_size}B"
    is_text = is_text_file(filename)

    # Create job in Chat's inbox for processing
    chat_inbox = get_agent_inbox_job("chat")
    parent_id = chat_inbox["id"] if chat_inbox else None

    job = create_job(
        name=f"Analyze upload: {filename}",
        description=f"""A file has been uploaded for analysis.

Filename: {filename}
Size: {file_size_str}
Type: {"text" if is_text else "binary"}

{"Use `read_asset` to read the file content, then extract identity-relevant information (interests, goals, concerns, biographical facts) and create appropriate memories using `add_memory`. Store analysis insights in long-term memory using `write_long_term_memory`." if is_text else "This is a binary file. Note its existence in the user's memory."}

After processing, complete this job with `complete_job`.""",
        tags=["upload", "analysis", "background"],
        assignees=["chat"],
        parent_id=parent_id,
        created_by="user"
    )

    # Save file as job asset
    write_asset_bytes(job["id"], filename, content_bytes)

    # Add to user's short-term memory
    add_memory(
        short_description=f"Uploaded {filename}",
        type="thing",
        agent_id="user"
    )

    return {
        "status": "uploaded",
        "filename": filename,
        "job_id": job["id"],
        "size": file_size_str,
        "message": "File uploaded. Analysis job created."
    }
