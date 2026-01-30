"""Preview command - Extract Open Graph metadata for link previews."""

import json
import re
from typing import Optional

import typer

from skills.web.lib.http import HTTPClient


def _extract_og_metadata(html: str, url: str) -> dict:
    """Extract Open Graph and other metadata from HTML.

    Falls back to standard meta tags and title if OG tags aren't available.

    Args:
        html: HTML content
        url: Original URL (for fallback domain extraction)

    Returns:
        Dict with url, title, description, image, site_name
    """
    result = {"url": url}

    # Try BeautifulSoup first for robust parsing
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        # Open Graph tags
        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")
        og_site = soup.find("meta", property="og:site_name")
        og_type = soup.find("meta", property="og:type")
        og_url = soup.find("meta", property="og:url")

        # Twitter card fallbacks
        tw_title = soup.find("meta", attrs={"name": "twitter:title"})
        tw_desc = soup.find("meta", attrs={"name": "twitter:description"})
        tw_image = soup.find("meta", attrs={"name": "twitter:image"})

        # Standard meta fallbacks
        meta_desc = soup.find("meta", attrs={"name": "description"})
        title_tag = soup.find("title")

        # Build result with fallback chain
        result["title"] = (
            (og_title and og_title.get("content")) or
            (tw_title and tw_title.get("content")) or
            (title_tag and title_tag.get_text(strip=True)) or
            None
        )

        result["description"] = (
            (og_desc and og_desc.get("content")) or
            (tw_desc and tw_desc.get("content")) or
            (meta_desc and meta_desc.get("content")) or
            None
        )

        result["image"] = (
            (og_image and og_image.get("content")) or
            (tw_image and tw_image.get("content")) or
            None
        )

        result["site_name"] = (
            (og_site and og_site.get("content")) or
            None
        )

        if og_type:
            result["type"] = og_type.get("content")

        if og_url:
            result["url"] = og_url.get("content") or url

    except ImportError:
        # Fallback to regex if BeautifulSoup not available
        def get_meta(pattern):
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            return match.group(1) if match else None

        result["title"] = (
            get_meta(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']') or
            get_meta(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']') or
            get_meta(r'<title>([^<]+)</title>')
        )

        result["description"] = (
            get_meta(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']') or
            get_meta(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:description["\']') or
            get_meta(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']')
        )

        result["image"] = (
            get_meta(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']') or
            get_meta(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']')
        )

        result["site_name"] = get_meta(
            r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)["\']'
        )

    # Clean up None values
    return {k: v for k, v in result.items() if v is not None}


def preview(
    url: str = typer.Argument(..., help="URL to extract preview metadata from"),
    render: bool = typer.Option(
        False, "--render", "-r",
        help="Output as render envelope for link-preview renderer"
    ),
    json_output: bool = typer.Option(
        False, "--json", "-j",
        help="Output as JSON"
    ),
    timeout: int = typer.Option(
        15, "--timeout", "-t",
        help="Request timeout in seconds"
    ),
):
    """Extract Open Graph metadata for link previews.

    Fetches a URL and extracts Open Graph, Twitter Card, and standard
    meta tags to build a link preview. Use --render to output a render
    envelope for the link-preview renderer.

    Examples:
        web preview https://example.com
        web preview https://example.com --render
        web preview https://example.com --json
    """
    # Fetch the page
    try:
        client = HTTPClient(timeout=timeout, user_agent="Euno/1.0 (Preview)")
        response = client.get(url)

        if not response.ok:
            typer.echo(f"Error: HTTP {response.status} fetching {url}", err=True)
            raise typer.Exit(1)

        html = response.text()

    except ConnectionError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    # Extract metadata
    metadata = _extract_og_metadata(html, url)

    # Output based on format
    if render:
        envelope = {
            "renderer": "link-preview",
            "data": metadata,
            "display": "embed"
        }
        typer.echo(json.dumps(envelope))
    elif json_output:
        typer.echo(json.dumps(metadata, indent=2))
    else:
        # Human-readable output
        typer.echo(f"URL: {metadata.get('url', url)}")
        if metadata.get("title"):
            typer.echo(f"Title: {metadata['title']}")
        if metadata.get("description"):
            typer.echo(f"Description: {metadata['description']}")
        if metadata.get("image"):
            typer.echo(f"Image: {metadata['image']}")
        if metadata.get("site_name"):
            typer.echo(f"Site: {metadata['site_name']}")
        if metadata.get("type"):
            typer.echo(f"Type: {metadata['type']}")
