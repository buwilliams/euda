"""Watch commands - monitor pages for changes."""

import sys
from typing import Optional

import typer

from skills.web.lib.storage import (
    load_watches,
    get_watch,
    add_watch,
    remove_watch,
    update_watch,
    load_snapshot,
    save_snapshot,
)
from skills.common import HTTPClient, extract_main_content, clean_html


app = typer.Typer(no_args_is_help=True)


@app.command("add")
def watch_add(
    url: str = typer.Argument(..., help="URL to monitor"),
    name: Optional[str] = typer.Option(None, "--name", help="Display name for this watch"),
    interval: int = typer.Option(24, "--interval", help="Check interval in hours"),
    credentials: Optional[str] = typer.Option(None, "--credentials", help="Credential ID (future, stored but not used)"),
):
    """Add a page to the watch list."""
    # Fetch page to get title and establish baseline
    try:
        response = HTTPClient.fetch(
            url,
            headers={"Accept": "text/html,application/xhtml+xml"},
            timeout=30,
            user_agent="Euno/1.0 (Web Skill)",
        )
    except ConnectionError as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        raise typer.Exit(1)

    if not response.ok:
        print(f"HTTP error: {response.status}", file=sys.stderr)
        raise typer.Exit(1)

    html_content = response.text()

    # Extract content for snapshot
    result = extract_main_content(html_content)
    if result is None:
        print("Could not extract content", file=sys.stderr)
        raise typer.Exit(1)

    # Get title if name not provided
    if not name:
        name = _extract_title(html_content) or url

    # Add watch
    watch = add_watch(url, name, interval, credentials)
    if "error" in watch:
        print(watch["error"], file=sys.stderr)
        raise typer.Exit(1)

    # Save initial snapshot
    save_snapshot(watch["id"], result["content_text"])

    print(f"Added watch: {watch['id']}")
    print(f"Name: {name}")
    print(f"URL: {url}")
    print(f"Interval: {interval} hours")


@app.command("list")
def watch_list(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """List all watched pages."""
    watches = load_watches()

    if json_output:
        import json
        print(json.dumps({"watches": watches}, indent=2))
        return

    if not watches:
        print("No watches configured.")
        return

    print(f"Watches ({len(watches)}):")
    print()

    for w in watches:
        print(f"[{w['id']}] {w['name']}")
        print(f"  URL: {w['url']}")
        last_checked = w.get("last_checked", "never")
        print(f"  Interval: {w['check_interval_hours']}h | Last checked: {last_checked} | Changes: {w.get('change_count', 0)}")
        print()


@app.command("check")
def watch_check(
    watch_id: Optional[str] = typer.Option(None, "--id", help="Check specific watch"),
    all_watches: bool = typer.Option(False, "--all", help="Check all regardless of interval"),
):
    """Check watched pages for changes."""
    from datetime import datetime, timedelta

    watches = load_watches()
    if not watches:
        print("No watches configured.")
        return

    # Filter watches to check
    to_check = []
    now = datetime.now()

    for w in watches:
        if watch_id and w["id"] != watch_id:
            continue

        if all_watches or watch_id:
            to_check.append(w)
        else:
            # Check if due based on interval
            last = w.get("last_checked")
            if not last:
                to_check.append(w)
            else:
                last_dt = datetime.fromisoformat(last)
                if now - last_dt >= timedelta(hours=w["check_interval_hours"]):
                    to_check.append(w)

    if not to_check:
        print("No watches due for checking.")
        return

    changes = []

    for w in to_check:
        try:
            response = HTTPClient.fetch(
                w["url"],
                headers={"Accept": "text/html,application/xhtml+xml"},
                timeout=30,
                user_agent="Euno/1.0 (Web Skill)",
            )
        except ConnectionError as e:
            update_watch(w["id"], {
                "last_checked": now.isoformat(),
                "last_error": str(e),
                "error_count": w.get("error_count", 0) + 1,
            })
            continue

        if not response.ok:
            update_watch(w["id"], {
                "last_checked": now.isoformat(),
                "last_error": f"HTTP {response.status}",
                "error_count": w.get("error_count", 0) + 1,
            })
            continue

        html_content = response.text()
        result = extract_main_content(html_content)
        if result is None:
            continue

        current_content = result["content_text"]
        previous_content = load_snapshot(w["id"])

        # Check for changes
        if previous_content and current_content != previous_content:
            diff_summary = _summarize_diff(previous_content, current_content)
            changes.append({"watch": w, "summary": diff_summary})
            save_snapshot(w["id"], current_content)
            update_watch(w["id"], {
                "last_checked": now.isoformat(),
                "last_changed": now.isoformat(),
                "change_count": w.get("change_count", 0) + 1,
                "check_count": w.get("check_count", 0) + 1,
                "last_error": None,
            })
        else:
            if not previous_content:
                save_snapshot(w["id"], current_content)
            update_watch(w["id"], {
                "last_checked": now.isoformat(),
                "check_count": w.get("check_count", 0) + 1,
                "last_error": None,
            })

    # Report results
    if not changes:
        print(f"Checked {len(to_check)} watches, no changes detected.")
    else:
        print(f"Changes detected in {len(changes)} watches:")
        print()
        for c in changes:
            print(f"[{c['watch']['id']}] {c['watch']['name']}")
            print(f"  {c['summary']}")
            print()


@app.command("remove")
def watch_remove(
    watch_id: str = typer.Argument(..., help="Watch ID to remove"),
):
    """Remove a page from the watch list."""
    watch = get_watch(watch_id)
    if not watch:
        print(f"Watch not found: {watch_id}", file=sys.stderr)
        raise typer.Exit(1)

    remove_watch(watch_id)
    print(f"Removed watch: {watch_id} ({watch['name']})")


@app.command("show")
def watch_show(
    watch_id: str = typer.Argument(..., help="Watch ID"),
    diff: bool = typer.Option(False, "--diff", help="Show content diff"),
):
    """Show details for a watched page."""
    watch = get_watch(watch_id)
    if not watch:
        print(f"Watch not found: {watch_id}", file=sys.stderr)
        raise typer.Exit(1)

    print(f"Watch: {watch['id']}")
    print(f"Name: {watch['name']}")
    print(f"URL: {watch['url']}")
    print(f"Interval: {watch['check_interval_hours']} hours")
    print(f"Added: {watch.get('added_at', 'unknown')}")
    print(f"Last checked: {watch.get('last_checked', 'never')}")
    print(f"Total checks: {watch.get('check_count', 0)}")
    print(f"Changes detected: {watch.get('change_count', 0)}")

    if watch.get("last_error"):
        print(f"Last error: {watch['last_error']}")

    if diff:
        content = load_snapshot(watch_id)
        if content:
            print()
            print("Current content snapshot:")
            print("---")
            print(content[:2000] + ("..." if len(content) > 2000 else ""))


def _extract_title(html: str) -> Optional[str]:
    """Extract page title from HTML."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        if title_tag:
            return clean_html(title_tag.get_text())
    except ImportError:
        pass
    return None


def _summarize_diff(old: str, new: str) -> str:
    """Create a simple summary of content changes."""
    old_lines = set(old.split("\n"))
    new_lines = set(new.split("\n"))

    added = len(new_lines - old_lines)
    removed = len(old_lines - new_lines)

    old_len = len(old)
    new_len = len(new)
    if old_len > 0:
        change_pct = abs(new_len - old_len) / old_len * 100
    else:
        change_pct = 100

    parts = []
    if added:
        parts.append(f"{added} lines added")
    if removed:
        parts.append(f"{removed} lines removed")
    parts.append(f"({change_pct:.0f}% size change)")

    return ", ".join(parts)
