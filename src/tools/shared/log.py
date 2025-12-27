"""
Log tools for reading and writing life log entries.
"""

import re
from datetime import datetime
from pathlib import Path

# Base paths
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
SHARED_DIR = DATA_DIR / "shared"
LOG_DIR = SHARED_DIR / "state" / "lifelog"


def ensure_year_dir(year: int) -> Path:
    """Ensure the year directory exists and return its path."""
    year_dir = LOG_DIR / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)
    return year_dir


# Maximum sentences for summarized content (data/information)
MAX_SENTENCES_SUMMARY = 7

# Entry types that preserve human expression (no length limit)
VERBATIM_TYPES = {
    'journal', 'reflection', 'thought', 'musing', 'note',
    'message', 'conversation', 'email', 'text', 'letter',
    'quote', 'idea', 'blog', 'writing'
}


def count_sentences(text: str) -> int:
    """Count sentences in text (approximate)."""
    # Split on sentence-ending punctuation followed by space or end
    sentences = re.split(r'[.!?]+(?:\s|$)', text.strip())
    # Filter out empty strings
    return len([s for s in sentences if s.strip()])


def write_log_entry(
    content: str,
    timestamp: str = None,
    source: str = "manual",
    locality: str = "",
    entry_type: str = "",
    temporal_confidence: str = "high",
    temporal_source: str = "explicit"
) -> str:
    """
    Write an entry to the life log.

    Args:
        content: The content of the entry
        timestamp: ISO timestamp (defaults to now)
        source: Data source (e.g., 'manual', 'photo', 'conversation')
        locality: Location if known
        entry_type: Type of entry - affects length validation:
            - Verbatim types (journal, message, etc.): no length limit
            - Summary types: max 7 sentences
        temporal_confidence: high, medium, or low
        temporal_source: How the timestamp was determined

    Returns:
        Confirmation message with file path, or error if too long
    """
    # Only validate length for non-verbatim entry types (summaries of data)
    entry_type_lower = entry_type.lower() if entry_type else ""
    is_verbatim = any(vtype in entry_type_lower for vtype in VERBATIM_TYPES)

    if not is_verbatim:
        sentence_count = count_sentences(content)
        if sentence_count > MAX_SENTENCES_SUMMARY:
            return (
                f"Error: Entry too long ({sentence_count} sentences). "
                f"Maximum is {MAX_SENTENCES_SUMMARY} sentences for summarized content. "
                f"Either condense the data, or use a verbatim entry_type "
                f"(journal, reflection, message, etc.) if this is human expression."
            )

    # Default timestamp to now
    if timestamp is None:
        timestamp = datetime.now().isoformat()

    # Parse the date from timestamp
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except ValueError:
        dt = datetime.now()
        timestamp = dt.isoformat()

    # Ensure year directory exists
    year_dir = ensure_year_dir(dt.year)

    # Build the entry
    entry = f"""---
{timestamp}
source: {source}
locality: {locality}
type: {entry_type}
temporal_confidence: {temporal_confidence}
temporal_source: {temporal_source}

{content}
---

"""

    # Write to log file
    log_file = year_dir / f"{dt.strftime('%Y-%m-%d')}.md"
    with open(log_file, 'a') as f:
        f.write(entry)

    # Update manifest
    update_manifest(year_dir, dt, source)

    return f"Entry written to {log_file}"


def update_manifest(year_dir: Path, dt: datetime, source: str):
    """Update the yearly manifest with this entry."""
    manifest_file = year_dir / "_manifest.md"

    date_str = dt.strftime('%Y-%m-%d')
    timestamp = datetime.now().isoformat()

    # Read existing manifest or create new
    if manifest_file.exists():
        with open(manifest_file, 'r') as f:
            manifest = f.read()
    else:
        manifest = f"# Manifest for {dt.year}\n\n"

    # Check if this date already has an entry
    if date_str not in manifest:
        manifest += f"- {date_str}: {source} | processed: {timestamp}\n"
    else:
        # Update the existing entry to add source
        lines = manifest.split('\n')
        for i, line in enumerate(lines):
            if line.startswith(f"- {date_str}:"):
                if source not in line:
                    # Add source if not already present
                    parts = line.split('|')
                    sources = parts[0].replace(f"- {date_str}:", "").strip()
                    if sources:
                        sources += f", {source}"
                    else:
                        sources = source
                    lines[i] = f"- {date_str}: {sources} | processed: {timestamp}"
                break
        manifest = '\n'.join(lines)

    with open(manifest_file, 'w') as f:
        f.write(manifest)


def read_log_entry(date: str) -> str:
    """
    Read log entries for a specific date.

    Args:
        date: Date string in YYYY-MM-DD format

    Returns:
        The log contents or a message if not found
    """
    try:
        dt = datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return f"Invalid date format: {date}. Use YYYY-MM-DD."

    log_file = LOG_DIR / str(dt.year) / f"{date}.md"

    if not log_file.exists():
        return f"No log entries found for {date}"

    with open(log_file, 'r') as f:
        return f.read()


def list_log_dates(year: int = None) -> str:
    """
    List all dates that have log entries.

    Args:
        year: Optional year to filter by

    Returns:
        List of dates with entries
    """
    if year:
        years = [year]
    else:
        years = [int(d.name) for d in LOG_DIR.iterdir() if d.is_dir() and d.name.isdigit()]

    dates = []
    for y in sorted(years):
        year_dir = LOG_DIR / str(y)
        if year_dir.exists():
            for f in sorted(year_dir.glob('*.md')):
                if not f.name.startswith('_'):
                    dates.append(f.stem)

    if not dates:
        return "No log entries found."

    return "Log entries exist for:\n" + "\n".join(f"- {d}" for d in dates)


def search_log(query: str, year: int = None, limit: int = 10) -> str:
    """
    Search log entries for a query string.

    Args:
        query: Text to search for (case-insensitive)
        year: Optional year to limit search
        limit: Maximum number of results to return

    Returns:
        Matching entries with dates and snippets
    """
    if year:
        years = [year]
    else:
        years = [int(d.name) for d in LOG_DIR.iterdir() if d.is_dir() and d.name.isdigit()]

    query_lower = query.lower()
    results = []

    for y in sorted(years, reverse=True):
        year_dir = LOG_DIR / str(y)
        if not year_dir.exists():
            continue

        for log_file in sorted(year_dir.glob('*.md'), reverse=True):
            if log_file.name.startswith('_'):
                continue

            with open(log_file, 'r') as f:
                content = f.read()

            if query_lower not in content.lower():
                continue

            # Parse entries and find matching ones
            entries = content.split('---')
            for entry in entries:
                entry = entry.strip()
                if not entry:
                    continue

                if query_lower in entry.lower():
                    # Extract timestamp (first line after ---)
                    lines = entry.split('\n')
                    timestamp = lines[0] if lines else "Unknown"

                    # Create snippet around the match
                    entry_lower = entry.lower()
                    idx = entry_lower.find(query_lower)
                    start = max(0, idx - 50)
                    end = min(len(entry), idx + len(query) + 50)
                    snippet = entry[start:end]
                    if start > 0:
                        snippet = "..." + snippet
                    if end < len(entry):
                        snippet = snippet + "..."

                    results.append({
                        "date": log_file.stem,
                        "timestamp": timestamp,
                        "snippet": snippet.replace('\n', ' ')
                    })

                    if len(results) >= limit:
                        break

            if len(results) >= limit:
                break

        if len(results) >= limit:
            break

    if not results:
        return f"No log entries found matching '{query}'"

    output = f"Found {len(results)} matching entries:\n\n"
    for r in results:
        output += f"**{r['date']}** ({r['timestamp'][:19]})\n"
        output += f"  {r['snippet']}\n\n"

    return output


def get_recent_entries(days: int = 7) -> str:
    """
    Get log entries from the last N days.

    Args:
        days: Number of days to look back

    Returns:
        Recent log entries
    """
    from datetime import timedelta

    today = datetime.now()
    entries = []

    for i in range(days):
        date = today - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        log_file = LOG_DIR / str(date.year) / f"{date_str}.md"

        if log_file.exists():
            with open(log_file, 'r') as f:
                content = f.read()
            entries.append(f"## {date_str}\n\n{content}")

    if not entries:
        return f"No log entries found in the last {days} days."

    return "\n".join(entries)


# Tool definitions for the LLM
LOG_TOOLS = [
    {
        "name": "write_log_entry",
        "description": "Write an entry to the life log. Use this to record events, thoughts, conversations, or any life data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The content of the log entry"
                },
                "timestamp": {
                    "type": "string",
                    "description": "ISO timestamp (e.g., 2024-01-15T09:30:00). Defaults to now if not specified."
                },
                "source": {
                    "type": "string",
                    "description": "Data source (e.g., 'manual', 'photo', 'conversation', 'article')"
                },
                "locality": {
                    "type": "string",
                    "description": "Location if known"
                },
                "entry_type": {
                    "type": "string",
                    "description": "Type of entry (e.g., 'note', 'photo', 'event', 'reflection')"
                },
                "temporal_confidence": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Confidence in the timestamp accuracy"
                },
                "temporal_source": {
                    "type": "string",
                    "description": "How the timestamp was determined (e.g., 'explicit', 'inferred', 'exif')"
                }
            },
            "required": ["content"]
        }
    },
    {
        "name": "read_log_entry",
        "description": "Read log entries for a specific date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date in YYYY-MM-DD format"
                }
            },
            "required": ["date"]
        }
    },
    {
        "name": "list_log_dates",
        "description": "List all dates that have log entries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "Optional year to filter by"
                }
            }
        }
    },
    {
        "name": "search_log",
        "description": "Search the life log for entries containing a query string.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Text to search for (case-insensitive)"
                },
                "year": {
                    "type": "integer",
                    "description": "Optional year to limit search"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default 10)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_recent_entries",
        "description": "Get log entries from the last N days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back (default 7)"
                }
            }
        }
    }
]

# Tool handlers mapping
LOG_HANDLERS = {
    "write_log_entry": write_log_entry,
    "read_log_entry": read_log_entry,
    "list_log_dates": list_log_dates,
    "search_log": search_log,
    "get_recent_entries": get_recent_entries,
}


# Test
if __name__ == "__main__":
    # Test writing an entry
    result = write_log_entry(
        content="This is a test log entry.",
        source="test",
        entry_type="note"
    )
    print(result)

    # Test reading
    today = datetime.now().strftime('%Y-%m-%d')
    print(read_log_entry(today))
