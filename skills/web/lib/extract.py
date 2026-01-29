"""Tavily extract functionality for webpage content extraction."""

import json
import os
from pathlib import Path
from typing import Any, Optional

import requests


def _get_tavily_config() -> dict[str, Any]:
    """Get Tavily configuration from environment or config file."""
    config = {
        "api_key": None,
        "timeout": 30,
    }

    config["api_key"] = os.environ.get("TAVILY_API_KEY")

    try:
        config_path = Path(__file__).parent.parent.parent.parent / "data" / "system" / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                system_config = json.load(f)
                tavily_config = system_config.get("tavily", {})
                config["timeout"] = tavily_config.get("timeout", config["timeout"])
    except Exception:
        pass

    return config


def extract_url(
    url: str,
    query: Optional[str] = None,
    format: str = "markdown",
    extract_depth: str = "basic",
) -> dict[str, Any]:
    """Extract content from a URL using Tavily Extract API.

    Args:
        url: The URL to extract content from
        query: Optional query for relevance-based chunk reranking
        format: Output format - "markdown" or "text"
        extract_depth: Extraction depth - "basic" (1 credit/5 URLs) or "advanced" (2 credits/5 URLs)

    Returns:
        Dict with 'content', 'url' keys, or 'error' key on failure
    """
    config = _get_tavily_config()

    if not config["api_key"]:
        return {"error": "TAVILY_API_KEY environment variable not set"}

    payload: dict[str, Any] = {
        "urls": url,
        "format": format,
        "extract_depth": extract_depth,
    }

    if query:
        payload["query"] = query

    try:
        response = requests.post(
            "https://api.tavily.com/extract",
            json=payload,
            timeout=config["timeout"],
            headers={
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json",
            },
        )

        if response.status_code == 401:
            return {"error": "Invalid Tavily API key"}
        if response.status_code == 403:
            return {"error": "URL not supported by Tavily Extract"}
        if response.status_code == 429:
            return {"error": "Tavily rate limit exceeded"}

        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        if not results:
            failed = data.get("failed_results", [])
            if failed:
                return {"error": f"Extraction failed: {failed[0].get('error', 'Unknown error')}"}
            return {"error": "No content extracted"}

        result = results[0]
        content = result.get("raw_content", "")

        return {
            "url": result.get("url", url),
            "content": content,
            "total_chars": len(content),
            "images": result.get("images", []),
            "query": query,
        }

    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to Tavily API"}
    except requests.exceptions.Timeout:
        return {"error": f"Tavily request timed out after {config['timeout']} seconds"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Tavily request failed: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Tavily returned invalid JSON"}
    except Exception as e:
        return {"error": f"Extraction failed: {str(e)}"}


def extract_urls(
    urls: list[str],
    query: Optional[str] = None,
    format: str = "markdown",
    extract_depth: str = "basic",
) -> dict[str, Any]:
    """Extract content from multiple URLs using Tavily Extract API.

    Args:
        urls: List of URLs to extract (max 20)
        query: Optional query for relevance-based chunk reranking
        format: Output format - "markdown" or "text"
        extract_depth: Extraction depth - "basic" or "advanced"

    Returns:
        Dict with 'results' list and 'failed' list, or 'error' key
    """
    if not urls:
        return {"error": "No URLs provided"}

    if len(urls) > 20:
        return {"error": "Maximum 20 URLs allowed per request"}

    config = _get_tavily_config()

    if not config["api_key"]:
        return {"error": "TAVILY_API_KEY environment variable not set"}

    payload: dict[str, Any] = {
        "urls": urls,
        "format": format,
        "extract_depth": extract_depth,
    }

    if query:
        payload["query"] = query

    try:
        response = requests.post(
            "https://api.tavily.com/extract",
            json=payload,
            timeout=config["timeout"] * 2,  # Longer timeout for batch
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

        results = []
        for r in data.get("results", []):
            content = r.get("raw_content", "")
            results.append({
                "url": r.get("url", ""),
                "content": content,
                "total_chars": len(content),
            })

        return {
            "results": results,
            "failed": data.get("failed_results", []),
            "count": len(results),
            "query": query,
        }

    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to Tavily API"}
    except requests.exceptions.Timeout:
        return {"error": "Tavily request timed out"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Tavily request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Extraction failed: {str(e)}"}
