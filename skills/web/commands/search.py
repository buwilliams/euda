"""Search command - search the web using Tavily API."""

import sys
from typing import Optional

import typer

from skills.web.lib.search import web_search


def search(
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

    Cost: 1 credit per search (basic) or 2 credits (advanced)

    Requires TAVILY_API_KEY environment variable to be set.
    """
    result = web_search(
        query=query,
        limit=min(limit, 20),
        topic=topic,
        time_range=time_range,
        search_depth=depth,
        include_answer=answer,
    )

    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
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
