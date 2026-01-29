"""Shared utilities for Euno skills.

This module provides common HTTP, content extraction, and parsing utilities
to reduce duplication across skills.

Example usage:
    from skills.common import HTTPClient, clean_html, parse_date

    # Make HTTP requests
    client = HTTPClient(timeout=10, user_agent="Euno/1.0 (MySkill)")
    response = client.get("https://example.com/api")
    if response.ok:
        data = response.json()

    # One-off fetch
    response = HTTPClient.fetch("https://example.com/page")

    # Clean HTML content
    plain_text = clean_html("<p>Hello <b>world</b></p>")

    # Parse dates
    iso_date = parse_date("Mon, 15 Jan 2024 10:30:00 +0000")
"""

from skills.common.http import HTTPClient, HTTPResponse
from skills.common.content import clean_html, extract_main_content
from skills.common.parsers import parse_json, parse_xml, parse_date

__all__ = [
    # HTTP
    "HTTPClient",
    "HTTPResponse",
    # Content
    "clean_html",
    "extract_main_content",
    # Parsers
    "parse_json",
    "parse_xml",
    "parse_date",
]
