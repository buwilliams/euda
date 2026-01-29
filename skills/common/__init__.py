"""Shared utilities for Euno skills.

This module provides common HTTP, content extraction, and parsing utilities
to reduce duplication across skills.

Example usage:
    from skills.common import HTTPClient, clean_html, parse_date

    # Make HTTP requests (rate-limited by default)
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

Rate limiting (enabled by default):
    from skills.common import RateLimitConfig, configure_rate_limiter

    # Customize rate limits (call once at startup)
    configure_rate_limiter(RateLimitConfig(
        min_request_interval=2.0,  # 2 seconds between requests per host
        max_concurrent_per_host=1,  # Only 1 request at a time per host
    ))

    # Or disable rate limiting for a specific client
    client = HTTPClient(rate_limit=False)
"""

from skills.common.http import (
    HTTPClient,
    HTTPResponse,
    RateLimitConfig,
    configure_rate_limiter,
)
from skills.common.content import clean_html, extract_main_content
from skills.common.parsers import parse_json, parse_xml, parse_date

__all__ = [
    # HTTP
    "HTTPClient",
    "HTTPResponse",
    "RateLimitConfig",
    "configure_rate_limiter",
    # Content
    "clean_html",
    "extract_main_content",
    # Parsers
    "parse_json",
    "parse_xml",
    "parse_date",
]
