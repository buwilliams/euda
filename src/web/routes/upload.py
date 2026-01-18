"""
Upload API Route

Handles file uploads by:
1. Saving the file to data/agents/user/uploads/{date}/
2. Analyzing text files for identity extraction (LLM-powered)
3. Creating semantic memories (goals, interests, concerns)
4. Adding full content to user's long-term memory (for text files)
"""

import json
from datetime import datetime
from pathlib import Path

import openai
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

# Max content length for LLM analysis (50KB)
MAX_ANALYSIS_SIZE = 50 * 1024

# Analysis prompt for identity extraction
ANALYSIS_PROMPT = """Analyze this uploaded document and extract identity-relevant information.

Document filename: {filename}
Document content:
{content}

Return a JSON object with:
{{
  "document_type": "biography|essay|professional_profile|routine|journal|notes|other",
  "summary": "1-2 sentence summary of what this document is",
  "biographical_facts": ["fact1", "fact2", ...],
  "interests": ["interest1", "interest2", ...],
  "goals": ["goal1", "goal2", ...],
  "concerns": ["concern1", ...],
  "key_insights": ["insight1", "insight2", ...]
}}

Guidelines:
- Only include fields where you find relevant information
- biographical_facts: Name, family, location, career, education
- interests: Topics, hobbies, intellectual interests, subjects they write about
- goals: Aspirations, objectives, things they want to achieve
- concerns: Worries, fears, challenges they face
- key_insights: 3-5 most important takeaways about this person
- Be concise but accurate"""


async def analyze_document(filename: str, content: str) -> dict | None:
    """Analyze uploaded document for identity extraction.

    Uses gpt-4o-mini for fast, cheap analysis. Returns dict with
    extracted info, or None if analysis fails.

    Args:
        filename: Name of the uploaded file
        content: Text content of the file

    Returns:
        Extracted identity information or None on failure
    """
    # Truncate very long content
    if len(content) > MAX_ANALYSIS_SIZE:
        content = content[:MAX_ANALYSIS_SIZE] + "\n\n[Content truncated for analysis]"

    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": ANALYSIS_PROMPT.format(filename=filename, content=content)
            }],
            temperature=0.3,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"[Upload] Document analysis failed: {e}")
        return None


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

    Saves the file and analyzes it for identity extraction:
    - Text files: analyzed by LLM for biographical facts, interests, goals
    - All files: content stored in long-term memory
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

    analysis = None
    memories_created = []

    # For text files, analyze and add to memory
    if is_text and file_size <= MAX_TEXT_SIZE:
        try:
            text_content = content_bytes.decode("utf-8")

            # Analyze document for identity extraction
            analysis = await analyze_document(filename, text_content)

            # Store raw content in long-term memory
            memory_content = f"**Uploaded file:** {filename}\n\n```\n{text_content}\n```"
            write_long_term_memory(
                content=memory_content,
                agent_id="user",
                source="Upload"
            )

            # Create semantic memories from analysis
            if analysis:
                # Add interests as memories
                for interest in analysis.get("interests", [])[:3]:
                    add_memory(
                        short_description=f"Interest: {interest}",
                        type="idea",
                        agent_id="user"
                    )
                    memories_created.append(f"[idea] {interest}")

                # Add goals as memories
                for goal in analysis.get("goals", [])[:2]:
                    add_memory(
                        short_description=goal,
                        type="goal",
                        agent_id="user"
                    )
                    memories_created.append(f"[goal] {goal}")

                # Add concerns as memories
                for concern in analysis.get("concerns", [])[:2]:
                    add_memory(
                        short_description=concern,
                        type="concern",
                        agent_id="user"
                    )
                    memories_created.append(f"[concern] {concern}")

                # Store analysis summary in long-term memory
                if analysis.get("key_insights"):
                    insights_content = f"**Document analysis:** {filename}\n\n"
                    insights_content += f"Type: {analysis.get('document_type', 'unknown')}\n"
                    insights_content += f"Summary: {analysis.get('summary', 'N/A')}\n\n"
                    insights_content += "Key insights:\n"
                    for insight in analysis.get("key_insights", []):
                        insights_content += f"- {insight}\n"

                    if analysis.get("biographical_facts"):
                        insights_content += "\nBiographical facts:\n"
                        for fact in analysis.get("biographical_facts", []):
                            insights_content += f"- {fact}\n"

                    write_long_term_memory(
                        content=insights_content,
                        agent_id="user",
                        source="Upload Analysis"
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

    # Add main upload entry to short-term memory (with better description if analyzed)
    if analysis:
        doc_type = analysis.get("document_type", "document")
        summary = analysis.get("summary", f"Uploaded {filename}")
        # Truncate summary if too long
        if len(summary) > 100:
            summary = summary[:97] + "..."
        add_memory(
            short_description=f"Uploaded {doc_type}: {summary}",
            type="thing",
            agent_id="user"
        )
    else:
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
        "analyzed": analysis is not None,
        "memories_created": memories_created,
        "message": "File saved and analyzed." if analysis else "File saved."
    }
