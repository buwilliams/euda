"""Save command - fetch and save content as topic asset."""

import sys
import re
from typing import Optional
from urllib.parse import urlparse

import typer

from skills.common import HTTPClient, extract_main_content, clean_html


def save(
    url: str = typer.Argument(..., help="URL to fetch"),
    topic_id: str = typer.Argument(..., help="Topic to attach asset to"),
    filename: Optional[str] = typer.Option(None, "--filename", help="Asset filename"),
    format: str = typer.Option("markdown", "--format", help="Output format: text, markdown, html"),
    credentials: Optional[str] = typer.Option(None, "--credentials", help="Credential ID (future, currently ignored)"),
):
    """Fetch a URL and save content as a topic asset."""
    # credentials parameter accepted but not used yet
    _ = credentials

    if format not in ("text", "markdown", "html"):
        print(f"Invalid format: {format}. Use text, markdown, or html.", file=sys.stderr)
        raise typer.Exit(1)

    # Fetch the page
    try:
        response = HTTPClient.fetch(
            url,
            headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
            timeout=30,
            user_agent="Euno/1.0 (Web Skill)",
        )
    except ConnectionError as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        raise typer.Exit(1)

    if not response.ok:
        print(f"HTTP error: {response.status}", file=sys.stderr)
        raise typer.Exit(1)

    html_content = response.text()

    # Extract content
    result = extract_main_content(html_content)
    if result is None:
        print("Could not extract content", file=sys.stderr)
        raise typer.Exit(1)

    # Get title for filename generation
    title = _extract_title(html_content)

    # Generate filename if not provided
    if not filename:
        filename = _generate_filename(url, title, format)

    # Format content
    if format == "html":
        content = result["content"]
    elif format == "text":
        content = result["content_text"]
    else:  # markdown
        content = _to_markdown(url, title, result["content_text"])

    # Save via core skill
    from subprocess import run, PIPE

    proc = run(
        ["euno", "skills", "core", "assets", "write", topic_id, filename, content],
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        print(f"Failed to save asset: {proc.stderr}", file=sys.stderr)
        raise typer.Exit(1)

    # Report success
    size_kb = len(content.encode("utf-8")) / 1024
    print(f"Saved: {filename} ({size_kb:.1f} KB)")
    print(f"Topic: {topic_id}")


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


def _generate_filename(url: str, title: Optional[str], format: str) -> str:
    """Generate a filename from URL or title."""
    ext = {"text": "txt", "markdown": "md", "html": "html"}[format]

    if title:
        # Sanitize title for filename
        name = re.sub(r"[^\w\s-]", "", title.lower())
        name = re.sub(r"[\s]+", "-", name)
        name = name[:50]  # Limit length
    else:
        # Use URL path
        parsed = urlparse(url)
        name = parsed.path.strip("/").replace("/", "-") or "page"
        name = re.sub(r"[^\w-]", "", name)[:50]

    return f"{name}.{ext}"


def _to_markdown(url: str, title: Optional[str], text: str) -> str:
    """Convert to simple markdown format."""
    lines = []
    if title:
        lines.append(f"# {title}")
        lines.append("")
    lines.append(f"Source: {url}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(text)
    return "\n".join(lines)
