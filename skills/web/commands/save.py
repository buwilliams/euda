"""Save command - extract and save web content as topic asset."""

import sys
import re
from typing import Optional
from urllib.parse import urlparse

import typer

from skills.web.lib.extract import extract_url


def save(
    url: str = typer.Argument(..., help="URL to fetch"),
    topic_id: str = typer.Argument(..., help="Topic to attach asset to"),
    filename: Optional[str] = typer.Option(None, "--filename", help="Asset filename"),
    format: str = typer.Option("markdown", "--format", help="Output format: text or markdown"),
    depth: str = typer.Option("basic", "--depth", help="Extraction depth: basic or advanced"),
):
    """Extract content from a URL and save as a topic asset.

    Uses Tavily Extract API for high-quality content extraction.
    Cost: 1 credit per 5 URLs (basic) or 2 credits per 5 URLs (advanced)
    """
    if format not in ("text", "markdown"):
        print(f"Invalid format: {format}. Use text or markdown.", file=sys.stderr)
        raise typer.Exit(1)

    # Extract content using Tavily
    result = extract_url(
        url=url,
        format=format,
        extract_depth=depth,
    )

    if "error" in result:
        print(f"Extraction failed: {result['error']}", file=sys.stderr)
        raise typer.Exit(1)

    extracted_content = result.get("content", "")
    if not extracted_content:
        print("No content extracted", file=sys.stderr)
        raise typer.Exit(1)

    # Generate filename if not provided
    if not filename:
        filename = _generate_filename(url, format)

    # Format content
    if format == "text":
        content = extracted_content
    else:  # markdown
        content = _to_markdown(url, extracted_content)

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


def _generate_filename(url: str, format: str) -> str:
    """Generate a filename from URL."""
    ext = {"text": "txt", "markdown": "md"}[format]

    # Use URL path for filename
    parsed = urlparse(url)
    name = parsed.path.strip("/").replace("/", "-") or "page"
    name = re.sub(r"[^\w-]", "", name)[:50]

    return f"{name}.{ext}"


def _to_markdown(url: str, content: str) -> str:
    """Format content as markdown with source URL."""
    lines = [
        f"Source: {url}",
        "",
        "---",
        "",
        content,
    ]
    return "\n".join(lines)
