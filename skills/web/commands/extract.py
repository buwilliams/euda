"""Extract command - extract content from URLs using Tavily API."""

import sys
from typing import Optional

import typer

from skills.web.lib.extract import extract_url


def extract(
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
    result = extract_url(
        url=url,
        query=query,
        format=format,
        extract_depth=depth,
    )

    if "error" in result:
        print(f"Error: {result['error']}", file=sys.stderr)
        raise typer.Exit(1)

    print(f"URL: {result.get('url', url)}")
    print(f"Total: {result.get('total_chars', 0):,} chars")
    if query:
        print(f"Query: {query}")

    print()
    print(result.get("content", "No content extracted"))
