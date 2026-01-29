"""Search the web for current information and extract webpage content."""

import sys
from pathlib import Path
from typing import Optional

import typer

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

app = typer.Typer(
    name="web_search",
    help="Search the web for information and extract webpage content.",
    no_args_is_help=True,
)


@app.command("search")
def search_cmd(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(5, "--limit", "-l", help="Number of results (default: 5, max: 20)"),
    topic: Optional[str] = typer.Option(
        None, "--topic", "-t",
        help="Search topic: 'general', 'news', or 'finance'"
    ),
    time_range: Optional[str] = typer.Option(
        None, "--time-range", "-r",
        help="Filter by time: 'day', 'week', 'month', or 'year'"
    ),
    depth: Optional[str] = typer.Option(
        None, "--depth", "-d",
        help="Search depth: 'basic', 'advanced', 'fast', or 'ultra-fast'"
    ),
    answer: bool = typer.Option(
        False, "--answer", "-a",
        help="Include AI-generated answer summary"
    ),
):
    """Search the web using Tavily API.

    Returns a list of search results with titles, URLs, and snippets.
    Useful for finding facts, recent events, or verifying information.

    Requires TAVILY_API_KEY environment variable to be set.
    """
    from skills.web_search.lib.search import web_search

    result = web_search(
        query=query,
        limit=min(limit, 20),
        topic=topic,
        time_range=time_range,
        search_depth=depth,
        include_answer=answer,
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"Search results for: {query}")
    print(f"Found: {result.get('count', 0)} results")

    # Show AI answer if available
    if result.get("answer"):
        print()
        print("Answer:")
        print(result["answer"])

    print()

    for i, item in enumerate(result.get("results", []), 1):
        print(f"{i}. {item.get('title', 'No title')}")
        print(f"   URL: {item.get('url', '')}")
        snippet = item.get("snippet", "")
        if snippet:
            print(f"   {snippet[:200]}")
        print()


@app.command("extract")
def extract_cmd(
    url: str = typer.Argument(..., help="URL to extract content from"),
    query: Optional[str] = typer.Option(
        None, "--query", "-q",
        help="Rerank extracted content by relevance to this query"
    ),
    format: str = typer.Option(
        "markdown", "--format", "-f",
        help="Output format: 'markdown' or 'text'"
    ),
    depth: str = typer.Option(
        "basic", "--depth", "-d",
        help="Extraction depth: 'basic' (1 credit/5 URLs) or 'advanced' (2 credits/5 URLs)"
    ),
):
    """Extract content from a webpage using Tavily Extract API.

    Extracts the main content from a URL in markdown or text format.
    Use --query to rerank content chunks by relevance.

    Cost: 1 credit per 5 URLs (basic) or 2 credits per 5 URLs (advanced)

    Requires TAVILY_API_KEY environment variable to be set.
    """
    from skills.web_search.lib.extract import extract_url

    result = extract_url(
        url=url,
        query=query,
        format=format,
        extract_depth=depth,
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        raise typer.Exit(1)

    print(f"URL: {result.get('url', url)}")
    print(f"Total: {result.get('total_chars', 0):,} chars")
    if query:
        print(f"Query: {query}")

    print()
    print(result.get("content", "No content extracted"))


def main():
    """Entry point for the web_search skill CLI."""
    app()


if __name__ == "__main__":
    main()
