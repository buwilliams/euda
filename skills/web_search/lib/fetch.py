"""URL fetching and content extraction."""

import re
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup


def _extract_paragraphs(text: str, min_length: int = 50, target_size: int = 500) -> list[str]:
    """Split text into paragraphs.

    Args:
        text: The full text content
        min_length: Minimum paragraph length to include
        target_size: Target paragraph size when grouping lines

    Returns:
        List of paragraph strings
    """
    # First try splitting on double newlines
    paragraphs = re.split(r'\n\s*\n', text)

    # If we only got 1-2 chunks, the text uses single newlines
    # Fall back to grouping consecutive lines into chunks
    if len(paragraphs) <= 2:
        lines = text.split('\n')
        paragraphs = []
        current_chunk = []
        current_len = 0

        for line in lines:
            line = line.strip()
            if not line:
                # Empty line - flush current chunk if substantial
                if current_len >= min_length:
                    paragraphs.append(' '.join(current_chunk))
                current_chunk = []
                current_len = 0
                continue

            current_chunk.append(line)
            current_len += len(line) + 1

            # Flush chunk if it's big enough
            if current_len >= target_size:
                paragraphs.append(' '.join(current_chunk))
                current_chunk = []
                current_len = 0

        # Don't forget the last chunk
        if current_len >= min_length:
            paragraphs.append(' '.join(current_chunk))

    # Filter short fragments and clean up
    return [p.strip() for p in paragraphs if len(p.strip()) >= min_length]


def _score_paragraph(paragraph: str, query: str, query_terms: list[str]) -> float:
    """Score paragraph by keyword relevance.

    Args:
        paragraph: The paragraph text
        query: The full query string
        query_terms: Individual query terms

    Returns:
        Relevance score (higher is better)
    """
    text_lower = paragraph.lower()
    score = 0.0

    # Exact phrase match (highest weight)
    if query.lower() in text_lower:
        score += 10.0

    # Individual term matches
    for term in query_terms:
        count = text_lower.count(term.lower())
        score += count * 1.0

    # Normalize by paragraph length (prefer concise matches)
    if len(paragraph) > 0:
        score = score / (1 + len(paragraph) / 500)

    return score


def fetch_url(
    url: str,
    max_chars: int = 8000,
    offset: int = 0,
    query: Optional[str] = None
) -> dict[str, Any]:
    """Fetch and extract main text content from a URL.

    Args:
        url: The URL to fetch
        max_chars: Maximum characters to return (default: 8000)
        offset: Character offset to start from (default: 0, ignored if query is set)
        query: Optional search query for relevance-based extraction

    Returns:
        Dict with 'content', 'title', 'url', 'total_chars', 'mode' keys
        Additional keys for relevance mode: 'paragraphs_returned', 'paragraphs_total', 'query'
        Additional keys for sequential mode: 'offset', 'has_more'
        Returns 'error' key on failure
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Euno/1.0; +https://github.com/buwilliams/euno)"
        }
        response = requests.get(url, headers=headers, timeout=45)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract title
        title = ""
        if soup.title:
            title = soup.title.string or ""

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
            element.decompose()

        # Extract main content - try common content selectors first
        main_content = None
        for selector in ["main", "article", "[role='main']", ".content", "#content"]:
            main_content = soup.select_one(selector)
            if main_content:
                break

        if not main_content:
            # Fallback to body
            main_content = soup.find("body")

        if not main_content:
            return {"content": "", "title": title.strip(), "url": url}

        # Convert links to markdown format [text](url) before extracting text
        for a in main_content.find_all("a", href=True):
            href = a["href"]
            link_text = a.get_text(strip=True)
            if link_text and href:
                # Make relative URLs absolute
                if href.startswith("/"):
                    from urllib.parse import urljoin
                    href = urljoin(url, href)
                # Replace link with markdown format
                a.replace_with(f"[{link_text}]({href})")

        text = main_content.get_text(separator="\n", strip=True)

        # Clean up whitespace
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        full_text = "\n".join(lines)
        total_chars = len(full_text)

        # Query-based relevance extraction
        if query:
            paragraphs = _extract_paragraphs(full_text)
            if not paragraphs:
                return {
                    "content": full_text[:max_chars],
                    "title": title.strip(),
                    "url": url,
                    "total_chars": total_chars,
                    "paragraphs_returned": 1,
                    "paragraphs_total": 1,
                    "query": query,
                    "mode": "relevance",
                }

            # Score and sort paragraphs
            query_terms = [t for t in query.lower().split() if len(t) > 2]
            scored = [
                (p, _score_paragraph(p, query, query_terms))
                for p in paragraphs
            ]
            scored.sort(key=lambda x: x[1], reverse=True)

            # Collect top paragraphs until max_chars
            selected = []
            char_count = 0
            separator = "\n\n---\n\n"

            for para, score in scored:
                if score <= 0:
                    break
                para_len = len(para) + (len(separator) if selected else 0)
                if char_count + para_len > max_chars:
                    break
                selected.append(para)
                char_count += para_len

            # If no paragraphs matched, fall back to top by position
            if not selected:
                for para, _ in scored[:3]:
                    para_len = len(para) + (len(separator) if selected else 0)
                    if char_count + para_len > max_chars:
                        break
                    selected.append(para)
                    char_count += para_len

            content = separator.join(selected)
            return {
                "content": content,
                "title": title.strip(),
                "url": url,
                "total_chars": total_chars,
                "paragraphs_returned": len(selected),
                "paragraphs_total": len(paragraphs),
                "query": query,
                "mode": "relevance",
            }

        # Sequential offset-based extraction (default)
        if offset >= total_chars:
            return {
                "content": "",
                "title": title.strip(),
                "url": url,
                "total_chars": total_chars,
                "offset": offset,
                "has_more": False,
                "mode": "sequential",
                "note": f"Offset {offset} exceeds content length {total_chars}",
            }

        text = full_text[offset:offset + max_chars]
        end_pos = offset + len(text)
        has_more = end_pos < total_chars
        remaining = total_chars - end_pos

        # Add continuation hint if truncated
        if has_more:
            text += f"\n\n[Content truncated. {remaining:,} chars remaining. Use --offset {end_pos} to continue.]"

        return {
            "content": text,
            "title": title.strip(),
            "url": url,
            "total_chars": total_chars,
            "offset": offset,
            "has_more": has_more,
            "mode": "sequential",
        }

    except requests.exceptions.Timeout:
        return {"error": "Request timed out"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch URL: {str(e)}"}
    except Exception as e:
        return {"error": f"Error processing page: {str(e)}"}
