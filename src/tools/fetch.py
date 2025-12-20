"""
URL fetching tool for reading web content.

Includes tools for:
- fetch_url: Read any web content
- archive_my_content: Save user's own writing (blogs, articles) to the log
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from .log import write_log_entry


def fetch_url(url: str, max_length: int = 15000) -> str:
    """
    Fetch a URL and extract readable text content.

    Args:
        url: The URL to fetch
        max_length: Maximum characters to return (default 15000)

    Returns:
        The extracted text content, or an error message
    """
    # Validate URL
    try:
        parsed = urlparse(url)
        if not parsed.scheme:
            url = "https://" + url
            parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return f"Error: Invalid URL scheme '{parsed.scheme}'. Only http/https supported."
        if not parsed.netloc:
            return "Error: Invalid URL - no domain found."
    except Exception as e:
        return f"Error parsing URL: {e}"

    # Fetch the content
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; MeAndUs/1.0; +https://github.com/meandus)"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return "Error: Request timed out after 30 seconds."
    except requests.exceptions.RequestException as e:
        return f"Error fetching URL: {e}"

    # Parse HTML and extract text
    content_type = response.headers.get("Content-Type", "")

    if "text/html" in content_type:
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script, style, nav, footer, header elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            element.decompose()

        # Try to find main content
        main_content = (
            soup.find("article") or
            soup.find("main") or
            soup.find(class_="content") or
            soup.find(class_="post") or
            soup.find(class_="entry") or
            soup.body
        )

        if main_content:
            # Get text with some structure preserved
            text = main_content.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        # Clean up excessive whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)

        # Get title
        title = ""
        if soup.title:
            title = soup.title.string or ""

        # Build result
        result = f"# {title}\n\nSource: {url}\n\n{text}"

    elif "text/plain" in content_type:
        result = f"Source: {url}\n\n{response.text}"
    else:
        result = f"Source: {url}\n\nContent-Type: {content_type}\n\n{response.text[:max_length]}"

    # Truncate if needed
    if len(result) > max_length:
        result = result[:max_length] + "\n\n[Content truncated...]"

    return result


def archive_my_content(url: str, content_type: str = "blog", notes: str = "") -> str:
    """
    Archive the user's own content (blog posts, articles they wrote) to the life log.

    This saves the FULL content, not a summary, because the user's own writing
    reveals their thoughts, values, and perspective. This rich data helps the
    Values Agent understand who they really are.

    Args:
        url: The URL to the user's content
        content_type: Type of content - blog, article, essay, newsletter, etc.
        notes: Optional notes from the user about why this is meaningful

    Returns:
        Confirmation message
    """
    # Fetch with higher limit for personal content
    content = fetch_url(url, max_length=50000)

    if content.startswith("Error"):
        return content

    # Build the log entry
    entry_parts = [
        f"## My {content_type.title()}",
        "",
        content,
    ]

    if notes:
        entry_parts.extend([
            "",
            "---",
            "",
            f"**My notes:** {notes}"
        ])

    full_entry = "\n".join(entry_parts)

    # Write to the life log
    result = write_log_entry(
        content=full_entry,
        source=f"my_{content_type}",
        entry_type="personal_writing"
    )

    return f"Archived your {content_type} to the life log. The Values Agent will be able to learn from your writing."


# Tool definition for the LLM
FETCH_TOOLS = [
    {
        "name": "fetch_url",
        "description": "Fetch a URL and extract its readable text content. Use this for reading external content like news, documentation, or articles by OTHER people. For the user's OWN writing, use archive_my_content instead.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch (e.g., 'https://example.com/blog/post')"
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum characters to return (default 15000)"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "archive_my_content",
        "description": "Archive the user's OWN writing (their blog posts, articles, essays, newsletters) to the life log. Use this when the user shares a link to something THEY wrote - their personal content reveals their thoughts, values, and perspective. Saves the FULL content (not a summary) so the Values Agent can learn who they really are.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to the user's own content"
                },
                "content_type": {
                    "type": "string",
                    "enum": ["blog", "article", "essay", "newsletter", "post", "writing"],
                    "description": "Type of content (default: blog)"
                },
                "notes": {
                    "type": "string",
                    "description": "Optional notes from the user about why this content is meaningful to them"
                }
            },
            "required": ["url"]
        }
    }
]

# Tool handlers mapping
FETCH_HANDLERS = {
    "fetch_url": fetch_url,
    "archive_my_content": archive_my_content,
}


# Test
if __name__ == "__main__":
    # Test with a simple URL
    result = fetch_url("https://example.com")
    print(result[:500])
