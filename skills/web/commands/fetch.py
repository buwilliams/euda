"""Fetch command - retrieve and extract web content."""

import sys
from typing import Optional

import typer

from skills.common import HTTPClient, extract_main_content, clean_html


def fetch(
    url: str = typer.Argument(..., help="URL to fetch"),
    raw: bool = typer.Option(False, "--raw", help="Return raw HTML instead of extracted content"),
    timeout: int = typer.Option(30, "--timeout", help="Request timeout in seconds"),
    credentials: Optional[str] = typer.Option(None, "--credentials", help="Credential ID (future, currently ignored)"),
):
    """Fetch a URL and extract readable content."""
    # credentials parameter accepted but not used yet
    _ = credentials

    try:
        response = HTTPClient.fetch(
            url,
            headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
            timeout=timeout,
            user_agent="Euno/1.0 (Web Skill)",
        )
    except ConnectionError as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        raise typer.Exit(1)

    if not response.ok:
        print(f"HTTP error: {response.status}", file=sys.stderr)
        raise typer.Exit(1)

    html_content = response.text()

    if raw:
        print(html_content)
        return

    # Extract readable content
    result = extract_main_content(html_content)

    if result is None:
        print("Could not extract content (BeautifulSoup not available)", file=sys.stderr)
        raise typer.Exit(1)

    # Try to extract title
    title = _extract_title(html_content)

    # Output
    if title:
        print(f"Title: {title}")
    print(f"URL: {url}")
    print()
    print("---")
    print()
    print(result["content_text"])


def _extract_title(html: str) -> Optional[str]:
    """Extract page title from HTML."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        if title_tag:
            return clean_html(title_tag.get_text())
    except ImportError:
        pass
    return None
