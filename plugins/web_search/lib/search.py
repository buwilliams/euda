"""SearXNG web search functionality."""

import json
import os
from pathlib import Path
from typing import Any, Optional

import requests


def _get_searxng_config() -> dict[str, Any]:
    """Get SearXNG configuration from environment or config file.

    Priority:
    1. SEARXNG_URL environment variable
    2. data/system/config.json searxng section
    3. Default values
    """
    config = {
        "url": "http://localhost:8080",
        "default_engines": None,
        "default_categories": "general",
        "timeout": 30,
    }

    # Check environment variable first
    env_url = os.environ.get("SEARXNG_URL")
    if env_url:
        config["url"] = env_url.rstrip("/")
        return config

    # Try to read from config file
    try:
        config_path = Path(__file__).parent.parent.parent.parent / "data" / "system" / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                system_config = json.load(f)
                searxng_config = system_config.get("searxng", {})
                config["url"] = searxng_config.get("url", config["url"]).rstrip("/")
                config["default_engines"] = searxng_config.get("default_engines")
                config["default_categories"] = searxng_config.get("default_categories", config["default_categories"])
                config["timeout"] = searxng_config.get("timeout", config["timeout"])
    except Exception:
        pass

    return config


def web_search(
    query: str,
    limit: int = 5,
    engines: Optional[str] = None,
    categories: Optional[str] = None,
    time_range: Optional[str] = None,
    language: Optional[str] = None,
) -> dict[str, Any]:
    """Search the web using SearXNG.

    Args:
        query: Search query string
        limit: Maximum number of results (1-20)
        engines: Comma-separated engine list (e.g., "google,bing,duckduckgo")
        categories: Comma-separated categories (e.g., "general,news,science")
        time_range: Filter by time - "day", "month", or "year"
        language: Language code (e.g., "en", "de", "fr")

    Returns:
        Dict with 'results' list or 'error' key
    """
    if not query or not query.strip():
        return {"error": "Empty search query"}

    limit = max(1, min(limit, 20))
    config = _get_searxng_config()

    # Build request parameters
    params: dict[str, Any] = {
        "q": query.strip(),
        "format": "json",
    }

    # Use provided values or defaults from config
    if engines:
        params["engines"] = engines
    elif config["default_engines"]:
        params["engines"] = config["default_engines"]

    if categories:
        params["categories"] = categories
    elif config["default_categories"]:
        params["categories"] = config["default_categories"]

    if time_range and time_range in ("day", "month", "year"):
        params["time_range"] = time_range

    if language:
        params["language"] = language

    try:
        response = requests.get(
            f"{config['url']}/search",
            params=params,
            timeout=config["timeout"],
            headers={"Accept": "application/json"},
        )

        if response.status_code == 403:
            return {"error": "SearXNG JSON format not enabled. Enable it in settings.yml: search.formats: [html, json]"}

        response.raise_for_status()
        data = response.json()

        # Extract and format results
        results = data.get("results", [])[:limit]
        formatted_results = []

        for r in results:
            formatted_results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", ""),  # SearXNG uses "content" field
                "engine": r.get("engine", ""),
            })

        return {
            "query": query,
            "count": len(formatted_results),
            "results": formatted_results,
        }

    except requests.exceptions.ConnectionError:
        return {"error": f"Cannot connect to SearXNG at {config['url']}. Is the server running?"}
    except requests.exceptions.Timeout:
        return {"error": f"SearXNG request timed out after {config['timeout']} seconds"}
    except requests.exceptions.RequestException as e:
        return {"error": f"SearXNG request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "SearXNG returned invalid JSON. Ensure JSON format is enabled."}
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}
