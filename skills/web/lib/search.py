"""Tavily web search functionality."""

import json
import os
from pathlib import Path
from typing import Any, Optional

import requests


def _get_skill_data_dir() -> Path:
    """Get the web skill data directory."""
    data_dir = os.environ.get("EUNO_DATA_DIR")
    if data_dir:
        base = Path(data_dir)
    else:
        base = Path(__file__).parent.parent.parent.parent / "data"
    return base / "skills" / "web"


def _get_tavily_config() -> dict[str, Any]:
    """Get Tavily configuration from environment or config file.

    Priority:
    1. TAVILY_API_KEY environment variable (required)
    2. data/skills/web/config.json tavily section for defaults
    """
    config = {
        "api_key": None,
        "default_topic": "general",
        "default_depth": "basic",
        "timeout": 30,
    }

    # API key from environment (required)
    config["api_key"] = os.environ.get("TAVILY_API_KEY")

    # Try to read defaults from skill config file
    try:
        config_path = _get_skill_data_dir() / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                skill_config = json.load(f)
                tavily_config = skill_config.get("tavily", {})
                config["default_topic"] = tavily_config.get("default_topic", config["default_topic"])
                config["default_depth"] = tavily_config.get("default_depth", config["default_depth"])
                config["timeout"] = tavily_config.get("timeout", config["timeout"])
    except Exception:
        pass

    return config


def web_search(
    query: str,
    limit: int = 5,
    topic: Optional[str] = None,
    time_range: Optional[str] = None,
    search_depth: Optional[str] = None,
    include_answer: bool = False,
) -> dict[str, Any]:
    """Search the web using Tavily API.

    Args:
        query: Search query string
        limit: Maximum number of results (1-20)
        topic: Search topic - "general", "news", or "finance"
        time_range: Filter by time - "day", "week", "month", or "year"
        search_depth: Search depth - "basic", "advanced", "fast", or "ultra-fast"
        include_answer: Include AI-generated answer summary

    Returns:
        Dict with 'results' list, optional 'answer', or 'error' key
    """
    if not query or not query.strip():
        return {"error": "Empty search query"}

    config = _get_tavily_config()

    if not config["api_key"]:
        return {"error": "TAVILY_API_KEY environment variable not set"}

    limit = max(1, min(limit, 20))

    # Build request payload
    payload: dict[str, Any] = {
        "query": query.strip(),
        "max_results": limit,
    }

    # Use provided values or defaults from config
    if topic and topic in ("general", "news", "finance"):
        payload["topic"] = topic
    elif config["default_topic"]:
        payload["topic"] = config["default_topic"]

    if search_depth and search_depth in ("basic", "advanced", "fast", "ultra-fast"):
        payload["search_depth"] = search_depth
    elif config["default_depth"]:
        payload["search_depth"] = config["default_depth"]

    if time_range and time_range in ("day", "week", "month", "year"):
        payload["time_range"] = time_range

    if include_answer:
        payload["include_answer"] = True

    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json=payload,
            timeout=config["timeout"],
            headers={
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json",
            },
        )

        if response.status_code == 401:
            return {"error": "Invalid Tavily API key"}
        if response.status_code == 429:
            return {"error": "Tavily rate limit exceeded"}

        response.raise_for_status()
        data = response.json()

        # Extract and format results
        results = data.get("results", [])
        formatted_results = []

        for r in results:
            formatted_results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", ""),
                "score": r.get("score", 0),
            })

        result = {
            "query": query,
            "count": len(formatted_results),
            "results": formatted_results,
        }

        # Include answer if requested and available
        if include_answer and data.get("answer"):
            result["answer"] = data["answer"]

        return result

    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to Tavily API"}
    except requests.exceptions.Timeout:
        return {"error": f"Tavily request timed out after {config['timeout']} seconds"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Tavily request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Tavily returned invalid JSON"}
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}
