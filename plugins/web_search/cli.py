"""Web search plugin for Euno - Search the web and fetch pages using SearXNG."""

import sys
from pathlib import Path
from typing import Optional

import typer

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

app = typer.Typer(
    name="web_search",
    help="Search the web and fetch pages using SearXNG.",
    no_args_is_help=True,
)


@app.command("search")
def search_cmd(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(5, "--limit", "-l", help="Number of results (default: 5, max: 20)"),
    engines: Optional[str] = typer.Option(
        None, "--engines", "-e",
        help="Comma-separated engines (e.g., 'google,bing,duckduckgo')"
    ),
    categories: Optional[str] = typer.Option(
        None, "--categories", "-c",
        help="Comma-separated categories (e.g., 'general,news,science')"
    ),
    time_range: Optional[str] = typer.Option(
        None, "--time-range", "-t",
        help="Filter by time: 'day', 'month', or 'year'"
    ),
):
    """Search the web using SearXNG.

    Returns a list of search results with titles, URLs, and snippets.

    Configure SearXNG URL via SEARXNG_URL env var or data/system/config.json.
    """
    from plugins.web_search.lib.search import web_search

    result = web_search(
        query=query,
        limit=min(limit, 20),
        engines=engines,
        categories=categories,
        time_range=time_range,
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Search results for: {query}")
    print(f"Found: {result.get('count', 0)} results")
    print()

    for i, item in enumerate(result.get("results", []), 1):
        print(f"{i}. {item.get('title', 'No title')}")
        print(f"   URL: {item.get('url', '')}")
        snippet = item.get("snippet", "")
        if snippet:
            print(f"   {snippet[:200]}")
        engine = item.get("engine", "")
        if engine:
            print(f"   [via {engine}]")
        print()


@app.command("fetch")
def fetch_cmd(
    url: str = typer.Argument(..., help="URL to fetch"),
    query: Optional[str] = typer.Option(
        None, "--query", "-q",
        help="Extract paragraphs relevant to this query"
    ),
    max_chars: int = typer.Option(
        8000, "--max-chars", "-m",
        help="Maximum characters to return (default: 8000)"
    ),
    offset: int = typer.Option(
        0, "--offset", "-o",
        help="Character offset for sequential pagination (ignored if --query is set)"
    ),
):
    """Fetch a webpage and extract its main text content.

    Two modes:
    - With --query: Returns most relevant paragraphs matching the query
    - Without --query: Returns sequential chunks, use --offset to paginate
    """
    from plugins.web_search.lib.fetch import fetch_url

    result = fetch_url(url=url, max_chars=max_chars, offset=offset, query=query)

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    total = result.get('total_chars', 0)
    mode = result.get('mode', 'sequential')

    print(f"URL: {result.get('url', url)}")
    print(f"Title: {result.get('title', 'Unknown')}")

    if mode == "relevance":
        paras_returned = result.get('paragraphs_returned', 0)
        paras_total = result.get('paragraphs_total', 0)
        print(f"Query: {result.get('query', '')}")
        print(f"Paragraphs: {paras_returned} of {paras_total} (relevance mode)")
        print(f"Total page: {total:,} chars")
    else:
        current_offset = result.get('offset', 0)
        content_len = len(result.get('content', ''))
        print(f"Content: {current_offset:,}-{current_offset + content_len:,} of {total:,} chars (sequential mode)")

    print()
    print(result.get("content", "No content found"))


def main():
    """Entry point for the web-search plugin CLI."""
    app()


if __name__ == "__main__":
    main()
