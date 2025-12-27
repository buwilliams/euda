"""
Batch processor for ingestion - processes multiple files in a single API call.

Instead of the agent making tool calls (2+ API round trips per file),
batch processing sends all file content in one request and asks for
structured JSON output that we write locally.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.tools.shared.log import write_log_entry


# Identity paths
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
IDENTITY_DIR = DATA_DIR / "shared" / "state" / "identity"


def load_batch_system_prompt() -> str:
    """
    Load the ingestion agent identity for use as batch system prompt.

    Combines core identity + ingestion persona + batch-specific instructions.
    """
    # Load identity files
    core_file = IDENTITY_DIR / "_core.identity.md"
    persona_file = IDENTITY_DIR / "ingestion.identity.md"

    core = ""
    persona = ""

    if core_file.exists():
        with open(core_file, 'r') as f:
            core = f.read()

    if persona_file.exists():
        with open(persona_file, 'r') as f:
            persona = f.read()

    # Combine identity with batch-specific instructions
    identity = f"{core}\n\n---\n\n{persona}" if core and persona else ""

    # Add date context
    today = datetime.now().strftime('%Y-%m-%d')

    batch_instructions = f"""
---

Today's date is {today}.

## Batch Processing Mode

You are processing multiple files in a single request. For efficiency, return structured JSON instead of using tools.

Return ONLY valid JSON with log entries for each file. No other text or explanation."""

    return identity + batch_instructions if identity else batch_instructions.strip()


# Maximum files per batch (balances context usage vs API efficiency)
DEFAULT_BATCH_SIZE = 5

# Maximum total content size per batch (characters)
MAX_BATCH_CONTENT_SIZE = 100_000


def chunk_files(
    files: list[dict],
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_content_size: int = MAX_BATCH_CONTENT_SIZE
) -> list[list[dict]]:
    """
    Group files into batches for processing.

    Args:
        files: List of file dicts with 'content', 'name', etc.
        batch_size: Maximum files per batch
        max_content_size: Maximum total content characters per batch

    Returns:
        List of batches, each containing file dicts
    """
    batches = []
    current_batch = []
    current_size = 0

    for file_info in files:
        content_len = len(file_info.get('content', ''))

        # Check if adding this file exceeds limits
        if current_batch and (
            len(current_batch) >= batch_size or
            current_size + content_len > max_content_size
        ):
            batches.append(current_batch)
            current_batch = []
            current_size = 0

        current_batch.append(file_info)
        current_size += content_len

    # Don't forget the last batch
    if current_batch:
        batches.append(current_batch)

    return batches


def build_batch_prompt(files: list[dict]) -> str:
    """
    Build a prompt for batch processing multiple files.

    Args:
        files: List of file dicts with 'name', 'content', 'category', 'temporal'

    Returns:
        Formatted prompt string
    """
    files_content = []

    for i, file_info in enumerate(files, 1):
        file_section = f"""=== FILE {i}: {file_info['name']} ===
Category: {file_info.get('category', 'unknown')}
"""
        if file_info.get('temporal'):
            t = file_info['temporal']
            file_section += f"Temporal hint: {t.get('timestamp', 'unknown')} (confidence: {t.get('confidence', 'unknown')}, source: {t.get('source', 'unknown')})\n"

        file_section += f"""
Content:
{file_info['content']}
"""
        files_content.append(file_section)

    prompt = f"""Process these {len(files)} files and return log entries as JSON.

For EACH file, determine:

1. **CHECK FOR MULTIPLE DATES**: Does this file contain content from different dates?
   - Journal files often have entries like "January 15: ..." then "January 20: ..."
   - Message exports may span multiple days
   - **If content spans multiple dates → create SEPARATE entries for each date**

2. **Content type:**
   - PRESERVE VERBATIM (human expression): journals, musings, reflections, notes, messages, emails, conversations, quotes, ideas, blog posts
     → Record the actual words. Voice and expression matter.
   - SUMMARIZE (data/information): transactions, receipts, articles, reports, lists, logs
     → Compress to essence. 2-5 sentences max.

3. **Appropriate entry_type:**
   - "journal" / "reflection" / "thought" for personal writing
   - "message" / "conversation" / "email" for communications
   - "summary" for compressed data

4. **Timestamp (CRITICAL for historical content):**
   - If temporal hint has HIGH confidence → use it
   - If content contains dates (e.g., "January 15, 2016", "2016-01-15") → extract and use that date
   - If temporal hint has LOW confidence (file_mtime) but content is clearly from another time → use the content's actual date
   - **The timestamp must be when the content was WRITTEN, not when it was uploaded**
   - Historical content from 2016 MUST have a 2016 timestamp

Return ONLY valid JSON in this exact format (no other text):
{{
  "entries": [
    {{
      "file_name": "journal_2016.txt",
      "content": "January 15 entry content...",
      "timestamp": "2016-01-15T10:00:00",
      "source": "text_file",
      "entry_type": "journal",
      "temporal_confidence": "high",
      "temporal_source": "content"
    }},
    {{
      "file_name": "journal_2016.txt",
      "content": "January 20 entry content...",
      "timestamp": "2016-01-20T10:00:00",
      "source": "text_file",
      "entry_type": "journal",
      "temporal_confidence": "high",
      "temporal_source": "content"
    }}
  ]
}}

IMPORTANT:
- **One file can produce MULTIPLE entries if it contains content from different dates**
- For verbatim content, preserve the exact words
- For data, summarize in 2-5 sentences
- **timestamp is REQUIRED for historical content** - extract dates from content
- timestamp can only be null if absolutely no date can be determined
- temporal_confidence: "high" (from content/filename), "medium" (inferred), "low" (uncertain)
- temporal_source: how you determined the timestamp (e.g., "filename", "content", "metadata", "temporal_hint")

FILES TO PROCESS:
{''.join(files_content)}"""

    return prompt


def parse_batch_response(response: str, expected_count: int) -> list[dict]:
    """
    Parse the AI's JSON response into log entry dicts.

    Args:
        response: Raw response from the AI
        expected_count: Number of entries we expect

    Returns:
        List of entry dicts ready for write_log_entry

    Raises:
        ValueError: If response cannot be parsed or validation fails
    """
    # Try to find JSON in the response
    response = response.strip()

    # Handle case where response has markdown code blocks
    if '```json' in response:
        match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if match:
            response = match.group(1)
    elif '```' in response:
        match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
        if match:
            response = match.group(1)

    # Try to parse JSON
    try:
        data = json.loads(response)
    except json.JSONDecodeError as e:
        # Try to find JSON object in response
        match = re.search(r'\{[\s\S]*\}', response)
        if match:
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                raise ValueError(f"Could not parse JSON from response: {e}")
        else:
            raise ValueError(f"No valid JSON found in response: {e}")

    # Extract entries
    if isinstance(data, dict) and 'entries' in data:
        entries = data['entries']
    elif isinstance(data, list):
        entries = data
    else:
        raise ValueError(f"Unexpected response format: expected 'entries' list")

    if not isinstance(entries, list):
        raise ValueError(f"'entries' must be a list, got {type(entries)}")

    # Validate entry count
    if len(entries) != expected_count:
        # Log warning but don't fail - partial results are better than none
        print(f"Warning: Expected {expected_count} entries, got {len(entries)}")

    # Validate and normalize entries
    validated = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue

        # Required field
        content = entry.get('content', '').strip()
        if not content:
            continue

        validated.append({
            'content': content,
            'timestamp': entry.get('timestamp'),
            'source': entry.get('source', 'batch_ingestion'),
            'locality': entry.get('locality', ''),
            'entry_type': entry.get('entry_type', 'note'),
            'temporal_confidence': entry.get('temporal_confidence', 'medium'),
            'temporal_source': entry.get('temporal_source', 'batch_inferred'),
            'file_name': entry.get('file_name', '')
        })

    return validated


def write_batch_entries(entries: list[dict]) -> list[dict]:
    """
    Write parsed entries to the log.

    Args:
        entries: List of entry dicts from parse_batch_response

    Returns:
        List of results with status for each entry
    """
    results = []

    for entry in entries:
        file_name = entry.pop('file_name', '')  # Remove from entry before writing

        try:
            result = write_log_entry(
                content=entry['content'],
                timestamp=entry.get('timestamp'),
                source=entry.get('source', 'batch_ingestion'),
                locality=entry.get('locality', ''),
                entry_type=entry.get('entry_type', 'note'),
                temporal_confidence=entry.get('temporal_confidence', 'medium'),
                temporal_source=entry.get('temporal_source', 'batch_inferred')
            )

            results.append({
                'file_name': file_name,
                'status': 'success',
                'result': result
            })

        except Exception as e:
            results.append({
                'file_name': file_name,
                'status': 'error',
                'error': str(e)
            })

    return results


def process_batch_with_provider(
    files: list[dict],
    provider,
    system_prompt: str = None
) -> tuple[list[dict], list[dict]]:
    """
    Process a batch of files using the LLM provider.

    Args:
        files: List of file dicts with 'name', 'content', 'category', 'temporal'
        provider: LLM provider instance
        system_prompt: Optional system prompt (defaults to ingestion identity)

    Returns:
        Tuple of (successful_results, failed_files)
    """
    if not files:
        return [], []

    # Use ingestion identity as system prompt if not provided
    if system_prompt is None:
        system_prompt = load_batch_system_prompt()

    # Build the batch prompt
    prompt = build_batch_prompt(files)

    # Call the provider (single API call!)
    # max_tokens=None uses the config value from llm.json
    try:
        response = provider.complete(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=system_prompt
        )
    except Exception as e:
        # Return all files as failed
        return [], [{'file': f, 'error': str(e)} for f in files]

    # Parse the response
    try:
        entries = parse_batch_response(response, len(files))
    except ValueError as e:
        # Failed to parse - return all as failed
        return [], [{'file': f, 'error': f"Parse error: {e}"} for f in files]

    # Write entries to log
    results = write_batch_entries(entries)

    # Separate successful and failed
    successful = [r for r in results if r['status'] == 'success']
    failed = [
        {'file': files[i], 'error': r.get('error', 'Unknown error')}
        for i, r in enumerate(results)
        if r['status'] != 'success' and i < len(files)
    ]

    return successful, failed


# For testing
if __name__ == "__main__":
    # Test chunking
    test_files = [
        {'name': f'file{i}.txt', 'content': f'Content {i}' * 100}
        for i in range(12)
    ]

    batches = chunk_files(test_files, batch_size=5)
    print(f"Created {len(batches)} batches from {len(test_files)} files")
    for i, batch in enumerate(batches):
        print(f"  Batch {i+1}: {len(batch)} files")

    # Test prompt building
    sample_files = [
        {
            'name': 'journal_2024-12-24.txt',
            'content': 'Today I reflected on the year...',
            'category': 'text',
            'temporal': {'timestamp': '2024-12-24', 'confidence': 'high', 'source': 'filename'}
        },
        {
            'name': 'receipt.txt',
            'content': 'Amazon order #123: Widget $29.99',
            'category': 'text',
            'temporal': None
        }
    ]
    prompt = build_batch_prompt(sample_files)
    print(f"\nSample prompt ({len(prompt)} chars):")
    print(prompt[:500] + "...")
