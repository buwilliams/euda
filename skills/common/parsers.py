"""Response parsing utilities for common formats."""

import json
import re
from datetime import datetime
from typing import Any, Optional
from xml.etree import ElementTree as ET


def parse_json(data: bytes, encoding: str = "utf-8") -> tuple[Optional[Any], Optional[str]]:
    """Safely parse JSON data.

    Args:
        data: Raw bytes to parse
        encoding: Text encoding (default: utf-8)

    Returns:
        Tuple of (parsed_data, error_message). One will be None.

    Example:
        data, error = parse_json(response.body)
        if error:
            return {"error": error}
    """
    try:
        return json.loads(data.decode(encoding)), None
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {e}"
    except UnicodeDecodeError as e:
        return None, f"Encoding error: {e}"


def parse_xml(data: bytes) -> tuple[Optional[ET.Element], Optional[str]]:
    """Safely parse XML data.

    Args:
        data: Raw bytes to parse

    Returns:
        Tuple of (root_element, error_message). One will be None.

    Example:
        root, error = parse_xml(response.body)
        if error:
            return {"error": error}
    """
    try:
        return ET.fromstring(data), None
    except ET.ParseError as e:
        return None, f"Invalid XML: {e}"


def parse_date(date_str: str) -> Optional[str]:
    """Parse various date formats to ISO format.

    Handles common RSS/Atom date formats including RFC 822 and ISO 8601.

    Args:
        date_str: Date string in various formats

    Returns:
        ISO format datetime string, or None if parsing fails
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    # Common date formats in RSS/Atom feeds
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",  # RFC 822 (RSS)
        "%a, %d %b %Y %H:%M:%S %Z",  # RFC 822 with timezone name
        "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601 (Atom)
        "%Y-%m-%dT%H:%M:%SZ",  # ISO 8601 UTC
        "%Y-%m-%d %H:%M:%S",  # Simple datetime
        "%Y-%m-%d",  # Simple date
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.isoformat()
        except ValueError:
            continue

    # Try parsing without timezone for malformed dates
    try:
        # Handle dates like "2024-01-15T10:30:00+00:00"
        if "+" in date_str or date_str.endswith("Z"):
            clean = re.sub(r"[Z+].*$", "", date_str)
            dt = datetime.fromisoformat(clean)
            return dt.isoformat()
    except ValueError:
        pass

    return None
