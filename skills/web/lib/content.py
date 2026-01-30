"""HTML content extraction utilities."""

import html
import re
from typing import Optional


def clean_html(text: str) -> str:
    """Strip HTML tags and decode entities.

    Args:
        text: HTML string to clean

    Returns:
        Plain text with tags removed and entities decoded
    """
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities
    text = html.unescape(text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_main_content(html_content: str) -> Optional[dict]:
    """Extract main article content from an HTML page.

    Uses BeautifulSoup to find the primary content area by looking for
    semantic elements (article, main) or common content class/id patterns.

    Args:
        html_content: Full HTML document string

    Returns:
        Dict with 'content' (HTML) and 'content_text' (plain text),
        or None if BeautifulSoup not available or no content found
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return None

    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script, style, nav, header, footer, aside elements
    for tag in soup.find_all(
        ["script", "style", "nav", "header", "footer", "aside", "noscript"]
    ):
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
        for selector in [
            "post-content",
            "entry-content",
            "article-content",
            "post-body",
            "entry-body",
            "article-body",
            "content",
            "post",
            "entry",
        ]:
            content_elem = soup.find(class_=selector) or soup.find(id=selector)
            if content_elem:
                break

    # 4. Fall back to body
    if not content_elem:
        content_elem = soup.find("body")

    if not content_elem:
        return None

    # Get HTML and text
    content_html = str(content_elem)
    content_text = content_elem.get_text(separator=" ", strip=True)

    # Clean up excessive whitespace
    content_text = re.sub(r"\s+", " ", content_text).strip()

    return {
        "content": content_html,
        "content_text": content_text,
    }
