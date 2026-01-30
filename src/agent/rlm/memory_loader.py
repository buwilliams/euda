"""
RLM Memory Loader

Loads long-term memory into a format suitable for RLM exploration.
"""

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


# Base path for agent data
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"


def _parse_memory_file(file_path: Path) -> list[dict]:
    """Parse a long-term memory markdown file into entries.

    Args:
        file_path: Path to the markdown file

    Returns:
        List of entry dicts with date, time, source, content
    """
    if not file_path.exists():
        return []

    content = file_path.read_text()
    entries = []

    # Extract date from filename (yyyy-mm-dd.md)
    date_str = file_path.stem  # e.g., "2026-01-11"

    # Split by section headers (## time · source)
    # Pattern: ## HH:MM AM/PM · Source
    section_pattern = r'^## (\d{1,2}:\d{2} (?:AM|PM)) · (.+)$'

    current_time = None
    current_source = None
    current_content_lines = []

    for line in content.split('\n'):
        match = re.match(section_pattern, line)
        if match:
            # Save previous section
            if current_time and current_content_lines:
                entries.append({
                    "date": date_str,
                    "time": current_time,
                    "source": current_source,
                    "content": '\n'.join(current_content_lines).strip()
                })

            current_time = match.group(1)
            current_source = match.group(2)
            current_content_lines = []
        elif line.startswith('# Long-term Memory'):
            # Skip the file header
            continue
        else:
            current_content_lines.append(line)

    # Save last section
    if current_time and current_content_lines:
        entries.append({
            "date": date_str,
            "time": current_time,
            "source": current_source,
            "content": '\n'.join(current_content_lines).strip()
        })

    return entries


def load_long_term_memory(
    agent_id: str = "user",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: Optional[int] = None
) -> dict:
    """
    Load long-term memory into RLM-friendly format.

    Args:
        agent_id: Which agent's memory to load
        start_date: Start date (YYYY-MM-DD), defaults to beginning
        end_date: End date (YYYY-MM-DD), defaults to today
        days: If set, load last N days (overrides start_date)

    Returns:
        {
            "entries": [
                {"date": "2025-01-19", "time": "10:30 AM", "source": "Chat", "content": "..."},
                ...
            ],
            "by_date": {
                "2025-01-19": "full markdown content",
                ...
            },
            "by_year": {
                "2025": {"01": ["2025-01-19", ...], "02": [...]},
                ...
            },
            "metadata": {
                "total_entries": 365,
                "total_chars": 500000,
                "date_range": ["2024-01-19", "2025-01-19"],
                "agent_id": "user"
            }
        }
    """
    memory_dir = DATA_DIR / "agents" / agent_id / "memory" / "long-term"

    if not memory_dir.exists():
        return {
            "entries": [],
            "by_date": {},
            "by_year": {},
            "metadata": {
                "total_entries": 0,
                "total_chars": 0,
                "date_range": [],
                "agent_id": agent_id
            }
        }

    # Calculate date range
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end_dt = datetime.now()

    if days:
        start_dt = end_dt - timedelta(days=days)
    elif start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start_dt = None  # Load all

    # Collect all memory files
    all_entries = []
    by_date = {}
    by_year = {}
    dates_found = []

    # Iterate through year directories
    for year_dir in sorted(memory_dir.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue

        year = year_dir.name

        if year not in by_year:
            by_year[year] = {}

        # Iterate through date files
        for date_file in sorted(year_dir.glob("*.md")):
            date_str = date_file.stem  # e.g., "2026-01-11"

            try:
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                continue

            # Check date range
            if start_dt and file_date < start_dt:
                continue
            if end_dt and file_date > end_dt:
                continue

            dates_found.append(date_str)

            # Read full content
            content = date_file.read_text()
            by_date[date_str] = content

            # Parse into entries
            entries = _parse_memory_file(date_file)
            all_entries.extend(entries)

            # Track by year/month
            month = date_str[5:7]  # Extract MM
            if month not in by_year[year]:
                by_year[year][month] = []
            by_year[year][month].append(date_str)

    # Calculate total characters
    total_chars = sum(len(content) for content in by_date.values())

    # Sort entries by date/time
    all_entries.sort(key=lambda e: (e["date"], e.get("time", "")))

    return {
        "entries": all_entries,
        "by_date": by_date,
        "by_year": by_year,
        "metadata": {
            "total_entries": len(all_entries),
            "total_chars": total_chars,
            "date_range": [min(dates_found), max(dates_found)] if dates_found else [],
            "agent_id": agent_id,
            "dates_loaded": len(dates_found)
        }
    }


def get_memory_summary(agent_id: str = "user") -> dict:
    """Get a summary of available memory without loading all content.

    Args:
        agent_id: Which agent's memory to summarize

    Returns:
        Summary dict with counts and date ranges
    """
    memory_dir = DATA_DIR / "agents" / agent_id / "memory" / "long-term"

    if not memory_dir.exists():
        return {
            "available": False,
            "total_files": 0,
            "date_range": [],
            "years": []
        }

    dates = []
    years = set()

    for year_dir in memory_dir.iterdir():
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue

        years.add(year_dir.name)

        for date_file in year_dir.glob("*.md"):
            dates.append(date_file.stem)

    dates.sort()

    return {
        "available": len(dates) > 0,
        "total_files": len(dates),
        "date_range": [dates[0], dates[-1]] if dates else [],
        "years": sorted(years)
    }


# =============================================================================
# Lightweight utilities for API file access (UI browsing)
# =============================================================================

def read_memory_date(agent_id: str, date: str, offset: int = 0, limit: int = None) -> dict:
    """Read a single date's memory file for UI display.

    This is a lightweight utility for API routes that need to display
    specific dates. For semantic search or analysis, use RLM methods instead.

    Args:
        agent_id: Which agent's memory to read
        date: Date in YYYY-MM-DD format

    Returns:
        {
            "date": "2026-01-19",
            "content": "# Long-term Memory\n\n...",
            "exists": true,
            "offset": 0,
            "limit": 200,
            "line_count": 200,
            "total_lines": 950,
            "has_more": true
        }
    """
    year = date[:4]
    memory_dir = DATA_DIR / "agents" / agent_id / "memory" / "long-term"
    file_path = memory_dir / year / f"{date}.md"

    if not file_path.exists():
        return {
            "date": date,
            "content": "",
            "exists": False,
            "offset": offset,
            "limit": limit,
            "line_count": 0,
            "total_lines": 0,
            "has_more": False
        }

    try:
        content = file_path.read_text()
        lines = content.splitlines()
        total_lines = len(lines)
        start = max(0, offset)
        if limit is None:
            slice_lines = lines[start:]
        else:
            slice_lines = lines[start:start + max(0, limit)]
        slice_content = "\n".join(slice_lines)
        line_count = len(slice_lines)
        has_more = (start + line_count) < total_lines
        return {
            "date": date,
            "content": slice_content,
            "exists": True,
            "offset": start,
            "limit": limit,
            "line_count": line_count,
            "total_lines": total_lines,
            "has_more": has_more
        }
    except Exception as e:
        return {
            "date": date,
            "content": "",
            "exists": False,
            "offset": offset,
            "limit": limit,
            "line_count": 0,
            "total_lines": 0,
            "has_more": False,
            "error": str(e)
        }


def list_memory_dates(agent_id: str) -> dict:
    """List all dates with memory entries for UI browsing.

    This is a lightweight utility for API routes that need to show
    available dates. For semantic search or analysis, use RLM methods instead.

    Args:
        agent_id: Which agent's memory to list

    Returns:
        {
            "dates": ["2026-01-19", "2026-01-18", ...],
            "total": 42
        }
    """
    memory_dir = DATA_DIR / "agents" / agent_id / "memory" / "long-term"

    if not memory_dir.exists():
        return {
            "dates": [],
            "total": 0
        }

    dates = []

    # Iterate through year directories (reverse chronological)
    for year_dir in sorted(memory_dir.iterdir(), reverse=True):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue

        # Collect all date files in this year (reverse chronological)
        for date_file in sorted(year_dir.glob("*.md"), reverse=True):
            dates.append(date_file.stem)

    return {
        "dates": dates,
        "total": len(dates)
    }
