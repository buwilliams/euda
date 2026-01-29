"""RSS and Atom feed parser."""

import html
import re
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional
from xml.etree import ElementTree as ET


# Namespace mappings for Atom and common RSS extensions
NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def _clean_html(text: str) -> str:
    """Strip HTML tags and decode entities."""
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities
    text = html.unescape(text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_date(date_str: str) -> Optional[str]:
    """Parse various date formats to ISO format.

    Handles common RSS/Atom date formats.
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    # Common date formats in RSS/Atom feeds
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",  # RFC 822 (RSS)
        "%a, %d %b %Y %H:%M:%S %Z",  # RFC 822 with timezone name
        "%Y-%m-%dT%H:%M:%S%z",       # ISO 8601 (Atom)
        "%Y-%m-%dT%H:%M:%SZ",        # ISO 8601 UTC
        "%Y-%m-%d %H:%M:%S",         # Simple datetime
        "%Y-%m-%d",                  # Simple date
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


def fetch_feed(url: str, timeout: int = 30) -> dict:
    """Fetch and parse an RSS or Atom feed.

    Args:
        url: Feed URL
        timeout: Request timeout in seconds

    Returns:
        Dict with feed metadata and posts, or error
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Euno/1.0 (RSS Reader)",
                "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content = response.read()

    except urllib.error.HTTPError as e:
        return {"error": f"HTTP error {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"error": f"Could not connect: {e.reason}"}
    except Exception as e:
        return {"error": f"Fetch failed: {str(e)}"}

    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        return {"error": f"Invalid XML: {str(e)}"}

    # Detect feed type and parse accordingly
    if root.tag == "{http://www.w3.org/2005/Atom}feed" or root.tag == "feed":
        return _parse_atom(root, url)
    elif root.tag == "rss" or root.find("channel") is not None:
        return _parse_rss(root, url)
    else:
        return {"error": f"Unknown feed format: {root.tag}"}


def _parse_rss(root: ET.Element, url: str) -> dict:
    """Parse an RSS feed."""
    channel = root.find("channel")
    if channel is None:
        return {"error": "RSS feed missing channel element"}

    feed = {
        "url": url,
        "format": "rss",
        "title": _clean_html(channel.findtext("title", "")),
        "description": _clean_html(channel.findtext("description", "")),
        "link": channel.findtext("link", ""),
        "posts": [],
    }

    for item in channel.findall("item"):
        post_id = item.findtext("guid") or item.findtext("link") or ""

        # Get content - try content:encoded first, then description
        content = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
        if not content:
            content = item.findtext("description", "")

        post = {
            "id": post_id,
            "title": _clean_html(item.findtext("title", "")),
            "link": item.findtext("link", ""),
            "content": content,
            "content_text": _clean_html(content),
            "published": _parse_date(item.findtext("pubDate", "")),
            "author": item.findtext("author") or item.findtext("{http://purl.org/dc/elements/1.1/}creator", ""),
        }
        feed["posts"].append(post)

    return feed


def _parse_atom(root: ET.Element, url: str) -> dict:
    """Parse an Atom feed."""
    # Handle namespaced and non-namespaced Atom
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    def find(elem: ET.Element, path: str) -> Optional[ET.Element]:
        """Find element with or without namespace."""
        result = elem.find(f"atom:{path}", ns)
        if result is None:
            result = elem.find(path)
        return result

    def findtext(elem: ET.Element, path: str, default: str = "") -> str:
        """Find text with or without namespace."""
        result = elem.findtext(f"atom:{path}", None, ns)
        if result is None:
            result = elem.findtext(path, default)
        return result or default

    def findall(elem: ET.Element, path: str) -> list:
        """Find all elements with or without namespace."""
        result = elem.findall(f"atom:{path}", ns)
        if not result:
            result = elem.findall(path)
        return result

    # Get feed link (prefer alternate, fall back to self)
    feed_link = ""
    for link in findall(root, "link"):
        rel = link.get("rel", "alternate")
        if rel == "alternate":
            feed_link = link.get("href", "")
            break
        elif rel == "self" and not feed_link:
            feed_link = link.get("href", "")

    feed = {
        "url": url,
        "format": "atom",
        "title": _clean_html(findtext(root, "title")),
        "description": _clean_html(findtext(root, "subtitle")),
        "link": feed_link,
        "posts": [],
    }

    for entry in findall(root, "entry"):
        post_id = findtext(entry, "id") or ""

        # Get content - prefer content, fall back to summary
        content_elem = find(entry, "content")
        if content_elem is not None and content_elem.text:
            content = content_elem.text
        else:
            content = findtext(entry, "summary", "")

        # Get post link
        post_link = ""
        for link in findall(entry, "link"):
            rel = link.get("rel", "alternate")
            if rel == "alternate":
                post_link = link.get("href", "")
                break

        # Get author
        author_elem = find(entry, "author")
        author = ""
        if author_elem is not None:
            author = findtext(author_elem, "name")

        post = {
            "id": post_id,
            "title": _clean_html(findtext(entry, "title")),
            "link": post_link,
            "content": content,
            "content_text": _clean_html(content),
            "published": _parse_date(findtext(entry, "published")) or _parse_date(findtext(entry, "updated")),
            "author": author,
        }
        feed["posts"].append(post)

    return feed


def fetch_full_content(url: str, timeout: int = 30) -> dict:
    """Fetch full article content from a post's URL.

    RSS feeds often contain only summaries. This fetches the actual page
    and extracts the main article content.

    Args:
        url: Post URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Dict with 'content' (HTML), 'content_text' (plain text), or 'error'
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Euno/1.0 (RSS Reader)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            html_content = response.read().decode("utf-8", errors="replace")

    except urllib.error.HTTPError as e:
        return {"error": f"HTTP error {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"error": f"Could not connect: {e.reason}"}
    except Exception as e:
        return {"error": f"Fetch failed: {str(e)}"}

    # Extract main content using BeautifulSoup
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return {"error": "BeautifulSoup not available"}

    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script, style, nav, header, footer, aside elements
    for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
        tag.decompose()

    # Try to find main content in order of preference
    content_elem = None

    # 1. Look for article tag
    content_elem = soup.find("article")

    # 2. Look for main tag
    if not content_elem:
        content_elem = soup.find("main")

    # 3. Look for common content class/id patterns
    if not content_elem:
        for selector in ["post-content", "entry-content", "article-content",
                         "post-body", "entry-body", "article-body",
                         "content", "post", "entry"]:
            content_elem = soup.find(class_=selector) or soup.find(id=selector)
            if content_elem:
                break

    # 4. Fall back to body
    if not content_elem:
        content_elem = soup.find("body")

    if not content_elem:
        return {"error": "Could not find content"}

    # Get HTML and text
    content_html = str(content_elem)
    content_text = content_elem.get_text(separator=" ", strip=True)

    # Clean up excessive whitespace
    content_text = re.sub(r"\s+", " ", content_text).strip()

    return {
        "content": content_html,
        "content_text": content_text,
        "url": url,
    }


def estimate_check_interval(posts: list[dict]) -> Optional[int]:
    """Estimate optimal check interval based on post frequency.

    Args:
        posts: List of posts with 'published' dates

    Returns:
        Suggested check interval in hours, or None if can't determine
    """
    # Get posts with valid dates
    dates = []
    for post in posts:
        if post.get("published"):
            try:
                dt = datetime.fromisoformat(post["published"].replace("Z", "+00:00"))
                dates.append(dt)
            except ValueError:
                continue

    if len(dates) < 2:
        return None

    # Sort by date
    dates.sort(reverse=True)

    # Calculate average gap between posts
    gaps = []
    for i in range(len(dates) - 1):
        gap = dates[i] - dates[i + 1]
        gaps.append(gap.total_seconds() / 3600)  # Convert to hours

    if not gaps:
        return None

    avg_gap = sum(gaps) / len(gaps)

    # Check interval should be roughly 1/4 of average gap
    # (so we check a few times between posts)
    # But clamp to reasonable bounds
    interval = max(1, min(168, int(avg_gap / 4)))  # 1 hour to 1 week

    return interval
