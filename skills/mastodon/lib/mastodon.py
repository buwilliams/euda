"""Mastodon API client for fetching public posts."""

from typing import Optional
import json

from skills.common import HTTPClient


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

    client = HTTPClient(
        base_url=f"https://{instance}",
        timeout=10,
        user_agent="Euno/1.0 (Mastodon)",
    )

    # First, look up the account ID
    try:
        response = client.get(f"/api/v1/accounts/lookup?acct={username}")
    except ConnectionError as e:
        return {"error": f"Could not connect to {instance}: {e}"}

    if response.status == 404:
        return {"error": f"Account @{username}@{instance} not found"}
    if not response.ok:
        return {"error": f"HTTP error looking up account: {response.status}"}

    try:
        account_data = response.json()
        account_id = account_data.get("id")
        if not account_id:
            return {"error": f"Account @{username}@{instance} not found"}
    except json.JSONDecodeError:
        return {"error": "Invalid response from Mastodon API"}

    # Fetch the account's statuses (public only)
    try:
        response = client.get(
            f"/api/v1/accounts/{account_id}/statuses"
            f"?limit={limit}&exclude_replies=true&exclude_reblogs=true"
        )
    except ConnectionError as e:
        return {"error": f"Could not connect to {instance}: {e}"}

    if not response.ok:
        return {"error": f"HTTP error fetching posts: {response.status}"}

    try:
        statuses = response.json()
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
