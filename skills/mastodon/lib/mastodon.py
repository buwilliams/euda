"""Mastodon API client for fetching public posts."""

from typing import Optional
import urllib.request
import urllib.error
import json


def get_mastodon_posts(
    username: str,
    instance: str = "mastodon.social",
    limit: int = 20
) -> dict:
    """Fetch recent public posts from a Mastodon account.

    Args:
        username: Mastodon username (without @)
        instance: Mastodon instance domain (default: mastodon.social)
        limit: Number of posts to fetch (max 40)

    Returns:
        Dict with posts list or error
    """
    limit = min(limit, 40)  # API max is 40

    # First, look up the account ID
    lookup_url = f"https://{instance}/api/v1/accounts/lookup?acct={username}"

    try:
        with urllib.request.urlopen(lookup_url, timeout=10) as response:
            account_data = json.loads(response.read().decode())
            account_id = account_data.get("id")

            if not account_id:
                return {"error": f"Account @{username}@{instance} not found"}

    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"error": f"Account @{username}@{instance} not found"}
        return {"error": f"HTTP error looking up account: {e.code}"}
    except urllib.error.URLError as e:
        return {"error": f"Could not connect to {instance}: {e.reason}"}
    except json.JSONDecodeError:
        return {"error": "Invalid response from Mastodon API"}

    # Fetch the account's statuses (public only)
    statuses_url = (
        f"https://{instance}/api/v1/accounts/{account_id}/statuses"
        f"?limit={limit}&exclude_replies=true&exclude_reblogs=true"
    )

    try:
        with urllib.request.urlopen(statuses_url, timeout=10) as response:
            statuses = json.loads(response.read().decode())

    except urllib.error.HTTPError as e:
        return {"error": f"HTTP error fetching posts: {e.code}"}
    except urllib.error.URLError as e:
        return {"error": f"Could not connect to {instance}: {e.reason}"}
    except json.JSONDecodeError:
        return {"error": "Invalid response from Mastodon API"}

    posts = []
    for status in statuses:
        posts.append({
            "id": status.get("id"),
            "content": status.get("content", ""),
            "created_at": status.get("created_at"),
            "url": status.get("url"),
            "reblogs_count": status.get("reblogs_count", 0),
            "favourites_count": status.get("favourites_count", 0),
            "replies_count": status.get("replies_count", 0),
        })

    return {
        "username": username,
        "instance": instance,
        "account_id": account_id,
        "posts": posts,
        "count": len(posts),
    }
