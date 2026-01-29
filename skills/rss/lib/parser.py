"""RSS and Atom feed parser."""

from datetime import datetime
from typing import Optional
from xml.etree import ElementTree as ET

from skills.common import HTTPClient, clean_html, extract_main_content, parse_date, parse_xml


def fetch_feed(url: str, timeout: int = 30) -> dict:
    """Fetch and parse an RSS or Atom feed.

    Args:
        url: Feed URL
        timeout: Request timeout in seconds

    Returns:
        Dict with feed metadata and posts, or error
    """
    try:
        response = HTTPClient.fetch(
            url,
            headers={"Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"},
            timeout=timeout,
            user_agent="Euno/1.0 (RSS Reader)",
        )
    except ConnectionError as e:
        return {"error": f"Could not connect: {e}"}

    if not response.ok:
        return {"error": f"HTTP error {response.status}"}

    root, error = parse_xml(response.body)
    if error:
        return {"error": error}

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
        "title": clean_html(channel.findtext("title", "")),
        "description": clean_html(channel.findtext("description", "")),
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
            "title": clean_html(item.findtext("title", "")),
            "link": item.findtext("link", ""),
            "content": content,
            "content_text": clean_html(content),
            "published": parse_date(item.findtext("pubDate", "")),
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
        "title": clean_html(findtext(root, "title")),
        "description": clean_html(findtext(root, "subtitle")),
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
            "title": clean_html(findtext(entry, "title")),
            "link": post_link,
            "content": content,
            "content_text": clean_html(content),
            "published": parse_date(findtext(entry, "published")) or parse_date(findtext(entry, "updated")),
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
        response = HTTPClient.fetch(
            url,
            headers={"Accept": "text/html,application/xhtml+xml"},
            timeout=timeout,
            user_agent="Euno/1.0 (RSS Reader)",
        )
    except ConnectionError as e:
        return {"error": f"Could not connect: {e}"}

    if not response.ok:
        return {"error": f"HTTP error {response.status}"}

    html_content = response.text()
    result = extract_main_content(html_content)

    if result is None:
        return {"error": "BeautifulSoup not available or could not find content"}

    return {
        "content": result["content"],
        "content_text": result["content_text"],
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
