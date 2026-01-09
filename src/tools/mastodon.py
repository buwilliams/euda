"""
Mastodon Tools - Read public posts from Mastodon accounts.
"""

import requests
from . import tool


@tool("get_mastodon_posts", "Get recent public posts from a Mastodon account")
def get_mastodon_posts(username: str, instance: str, limit: int = 20) -> dict:
    """Fetch recent public posts from a Mastodon account.

    Args:
        username: Mastodon username (without the @)
        instance: Mastodon instance domain (e.g., mastodon.social, fosstodon.org)
        limit: Number of posts to fetch (default 20, max 40)
    """
    try:
        # Look up account by username
        resp = requests.get(
            f"https://{instance}/api/v1/accounts/lookup",
            params={"acct": username},
            timeout=10
        )
        if resp.status_code == 404:
            return {"error": f"Account not found: {username}@{instance}"}
        if resp.status_code != 200:
            return {"error": f"Failed to lookup account: {resp.status_code}"}

        account_id = resp.json()["id"]

        # Fetch public statuses
        resp = requests.get(
            f"https://{instance}/api/v1/accounts/{account_id}/statuses",
            params={"limit": min(limit, 40), "exclude_replies": True},
            timeout=10
        )
        if resp.status_code != 200:
            return {"error": f"Failed to fetch posts: {resp.status_code}"}

        posts = []
        for status in resp.json():
            posts.append({
                "id": status["id"],
                "content": status["content"],
                "created_at": status["created_at"],
                "url": status["url"],
                "reblogs_count": status.get("reblogs_count", 0),
                "favourites_count": status.get("favourites_count", 0),
            })

        return {"posts": posts, "count": len(posts)}

    except requests.exceptions.Timeout:
        return {"error": f"Request to {instance} timed out"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
