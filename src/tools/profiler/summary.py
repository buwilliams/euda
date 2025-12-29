"""
Summary tools for the Summary Agent (The Historian).

Tools for reading logs, managing manifests, and writing yearly summaries.
"""

from datetime import datetime
from pathlib import Path
import hashlib

# Base paths - Summary agent uses shared log
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
SHARED_DIR = DATA_DIR / "shared"
LOG_DIR = SHARED_DIR / "state" / "lifelog"


def get_year_logs(year: int) -> str:
    """
    Read all log entries for a given year.

    Args:
        year: The year to read logs for

    Returns:
        All log entries concatenated with date headers
    """
    year_dir = LOG_DIR / str(year)

    if not year_dir.exists():
        return f"No logs found for {year}"

    logs = []
    for log_file in sorted(year_dir.glob('*.md')):
        if log_file.name.startswith('_'):
            continue

        date = log_file.stem
        with open(log_file, 'r') as f:
            content = f.read()

        logs.append(f"## {date}\n\n{content}")

    if not logs:
        return f"No log entries found for {year}"

    return f"# Log entries for {year}\n\n" + "\n".join(logs)


def get_manifest(year: int) -> str:
    """
    Read the manifest for a given year.

    Args:
        year: The year to read manifest for

    Returns:
        Manifest content or message if not found
    """
    manifest_file = LOG_DIR / str(year) / "_manifest.md"

    if not manifest_file.exists():
        return f"No manifest found for {year}"

    with open(manifest_file, 'r') as f:
        return f.read()


def get_summary(year: int) -> str:
    """
    Read the existing summary for a given year.

    Args:
        year: The year to read summary for

    Returns:
        Summary content or message if not found
    """
    summary_file = LOG_DIR / str(year) / "_summary.md"

    if not summary_file.exists():
        return f"No summary exists yet for {year}"

    with open(summary_file, 'r') as f:
        return f.read()


def write_summary(year: int, content: str) -> str:
    """
    Write or update the yearly summary.

    Args:
        year: The year to write summary for
        content: The summary content

    Returns:
        Confirmation message
    """
    year_dir = LOG_DIR / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)

    summary_file = year_dir / "_summary.md"

    # Add metadata header
    timestamp = datetime.now().isoformat()
    full_content = f"""# Summary for {year}

Generated: {timestamp}

{content}
"""

    with open(summary_file, 'w') as f:
        f.write(full_content)

    # Update manifest to record summary generation
    _update_manifest_summary(year)

    # Save the logs hash so we know when summary is up to date
    _save_logs_hash(year)

    return f"Summary written for {year}"


def _update_manifest_summary(year: int):
    """Update the manifest to record when summary was generated."""
    manifest_file = LOG_DIR / str(year) / "_manifest.md"
    timestamp = datetime.now().isoformat()

    if manifest_file.exists():
        with open(manifest_file, 'r') as f:
            content = f.read()
    else:
        content = f"# Manifest for {year}\n\n"

    # Add or update summary line
    if "Summary generated:" in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith("Summary generated:"):
                lines[i] = f"Summary generated: {timestamp}"
                break
        content = '\n'.join(lines)
    else:
        content += f"\nSummary generated: {timestamp}\n"

    with open(manifest_file, 'w') as f:
        f.write(content)


def check_summary_needed(year: int) -> str:
    """
    Check if a summary needs to be generated or updated.

    Compares log file hashes against last summary generation.

    Args:
        year: The year to check

    Returns:
        Status message indicating if summary is needed
    """
    year_dir = LOG_DIR / str(year)

    if not year_dir.exists():
        return f"No logs exist for {year}"

    summary_file = year_dir / "_summary.md"
    hash_file = year_dir / "_summary.hash"

    # Get current hash of all log files
    current_hash = _compute_logs_hash(year_dir)

    if not summary_file.exists():
        return f"Summary needed for {year}: No summary exists yet"

    # Check if hash matches
    if hash_file.exists():
        with open(hash_file, 'r') as f:
            stored_hash = f.read().strip()

        if stored_hash == current_hash:
            return f"Summary for {year} is up to date"

    return f"Summary needed for {year}: Log files have changed since last summary"


def _compute_logs_hash(year_dir: Path) -> str:
    """Compute a hash of all log files in a year directory."""
    hasher = hashlib.md5()

    for log_file in sorted(year_dir.glob('*.md')):
        if log_file.name.startswith('_'):
            continue
        with open(log_file, 'rb') as f:
            hasher.update(f.read())

    return hasher.hexdigest()


def _save_logs_hash(year: int):
    """Save the current logs hash after summary generation."""
    year_dir = LOG_DIR / str(year)
    hash_file = year_dir / "_summary.hash"

    current_hash = _compute_logs_hash(year_dir)
    with open(hash_file, 'w') as f:
        f.write(current_hash)


def list_years() -> str:
    """
    List all years that have log entries.

    Returns:
        List of years with entry counts
    """
    if not LOG_DIR.exists():
        return "No log directory found"

    years = []
    for year_dir in sorted(LOG_DIR.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue

        year = int(year_dir.name)
        log_count = len([f for f in year_dir.glob('*.md') if not f.name.startswith('_')])
        has_summary = (year_dir / "_summary.md").exists()

        years.append({
            "year": year,
            "log_count": log_count,
            "has_summary": has_summary
        })

    if not years:
        return "No years with log entries found"

    result = "Years with log entries:\n"
    for y in years:
        status = "has summary" if y["has_summary"] else "no summary"
        result += f"- {y['year']}: {y['log_count']} days logged ({status})\n"

    return result


# Tool definitions for the LLM
SUMMARY_TOOLS = [
    {
        "name": "get_year_logs",
        "description": "Read all log entries for a given year. Returns all entries concatenated with date headers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "The year to read logs for"
                }
            },
            "required": ["year"]
        }
    },
    {
        "name": "get_manifest",
        "description": "Read the manifest for a given year, which tracks processing state and sources.",
        "input_schema": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "The year to read manifest for"
                }
            },
            "required": ["year"]
        }
    },
    {
        "name": "get_summary",
        "description": "Read the existing summary for a given year.",
        "input_schema": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "The year to read summary for"
                }
            },
            "required": ["year"]
        }
    },
    {
        "name": "write_summary",
        "description": "Write or update the yearly summary. The summary should distill patterns, themes, key events, and insights from the year's logs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "The year to write summary for"
                },
                "content": {
                    "type": "string",
                    "description": "The summary content in markdown format"
                }
            },
            "required": ["year", "content"]
        }
    },
    {
        "name": "check_summary_needed",
        "description": "Check if a summary needs to be generated or updated for a given year.",
        "input_schema": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "The year to check"
                }
            },
            "required": ["year"]
        }
    },
    {
        "name": "list_years",
        "description": "List all years that have log entries, with counts and summary status.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

# Tool handlers mapping
SUMMARY_HANDLERS = {
    "get_year_logs": get_year_logs,
    "get_manifest": get_manifest,
    "get_summary": get_summary,
    "write_summary": write_summary,
    "check_summary_needed": check_summary_needed,
    "list_years": list_years,
}


# Test
if __name__ == "__main__":
    print(list_years())
    print()
    print(check_summary_needed(2025))
