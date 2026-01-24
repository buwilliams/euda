"""
Upload API Route

Handles file uploads by:
1. Storing text content in user's long-term memory
2. Creating a job for Chat to extract short-term memories
3. Consolidation will extract identity-relevant information later
"""

from pathlib import Path

from fastapi import APIRouter, UploadFile, File

from ...agent.cognition.reasoning.prompts import render_template
from ...tools.data.jobs import create_job, get_agent_inbox_job
from ...tools.data.memory import write_long_term_memory


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
    """Upload a file.

    Text files are stored in user's long-term memory.
    A job is created for Chat to extract short-term memories.
    """
    filename = file.filename
    content_bytes = await file.read()

    # Determine file type and size
    file_size = len(content_bytes)
    file_size_str = f"{file_size / 1024:.1f}KB" if file_size >= 1024 else f"{file_size}B"
    is_text = is_text_file(filename)

    # For text files, store content in user's long-term memory
    if is_text:
        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = content_bytes.decode("latin-1")

        # Write to long-term memory
        write_long_term_memory(
            content=f"**File: {filename}**\n\n{content}",
            agent_id="user",
            source="Upload"
        )

        # Create job to extract short-term memories
        chat_inbox = get_agent_inbox_job("chat")
        parent_id = chat_inbox["id"] if chat_inbox else None

        # Truncate content for job description
        truncated_content = content[:8000] + ("..." if len(content) > 8000 else "")

        job = create_job(
            name=f"euno:extract-memories:{filename}",
            description=render_template(
                "upload/extract_memories",
                filename=filename,
                content=truncated_content
            ),
            tags=["euno:internal"],
            assignee="chat",
            parent_id=parent_id,
            created_by="system"
        )

        return {
            "status": "uploaded",
            "filename": filename,
            "size": file_size_str,
            "job_id": job["id"],
            "message": "File stored in long-term memory. Extracting short-term memories."
        }

    # Binary files - just note the upload
    return {
        "status": "uploaded",
        "filename": filename,
        "size": file_size_str,
        "message": "Binary file uploaded (not stored in memory)."
    }
