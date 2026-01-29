# Web Skill Specification

Fetch, extract, and monitor web content for Euno agents.

## Overview

The web skill enables agents to retrieve information from the web. It is **not** a general search engine (that's handled by the Tavily skill) but rather a tool for:
- Fetching specific URLs
- Extracting readable content from pages
- Saving reference material to topics
- Monitoring pages for changes

Euno is a polite web citizen: all requests are rate-limited (1s minimum between requests per host, max 2 concurrent per host).

## Use Cases

| Pattern | Persistence | Example |
|---------|-------------|---------|
| **Lookup** | None (chat only) | Fetch a page to answer a question |
| **Search** | Short-term memory | Query a job board, compare options |
| **Reference** | Topic asset | Save documentation for later |
| **Monitor** | Trigger + memory | Watch for job postings, track changes |

## Directory Structure

```
skills/
├── common/              # Shared utilities (HTTPClient, content extraction)
└── web/
    ├── cli.py           # Typer CLI entry point
    ├── commands/
    │   ├── fetch.py     # Fetch and extract content
    │   ├── save.py      # Save content to topic assets
    │   └── watch.py     # Monitor pages for changes
    └── lib/
        ├── storage.py   # Watch list persistence
        └── diff.py      # Change detection
```

Data storage:
```
data/skills/web/
├── watches.json         # Watched pages
├── snapshots/           # Page snapshots for diff detection
│   └── {watch_id}.txt   # Last known content (plain text)
└── config.json          # Skill configuration
```

## Commands

### fetch

Fetch a URL and extract readable content.

```bash
web fetch <url> [--raw] [--timeout SECONDS] [--credentials ID]
```

**Arguments:**
- `url` — URL to fetch (required)
- `--raw` — Return raw HTML instead of extracted content
- `--timeout` — Request timeout in seconds (default: 30)
- `--credentials` — Credential ID for authenticated sites (future, currently ignored)

**Output:**
```
Title: Example Article
URL: https://example.com/article

---

[Extracted plain text content...]
```

**Errors:**
- Connection failed → exit 1, stderr message
- HTTP error (4xx/5xx) → exit 1, stderr with status code
- Content extraction failed → exit 1, stderr message

### save

Fetch a URL and save content as a topic asset.

```bash
web save <url> <topic_id> [--filename NAME] [--format FORMAT] [--credentials ID]
```

**Arguments:**
- `url` — URL to fetch (required)
- `topic_id` — Topic to attach asset to (required)
- `--filename` — Asset filename (default: derived from URL/title)
- `--format` — Output format: `text`, `markdown`, `html` (default: markdown)
- `--credentials` — Credential ID for authenticated sites (future, currently ignored)

**Output:**
```
Saved: documentation.md (12.4 KB)
Topic: abc123
```

**Behavior:**
- Fetches URL and extracts content
- Converts to requested format
- Saves as topic asset via core skill
- Returns confirmation with filename and size

### watch add

Add a page to the watch list for change monitoring.

```bash
web watch add <url> [--name NAME] [--interval HOURS] [--credentials ID]
```

**Arguments:**
- `url` — URL to monitor (required)
- `--name` — Display name for this watch (default: page title)
- `--interval` — Check interval in hours (default: 24)
- `--credentials` — Credential ID for authenticated sites (future, stored but not used)

**Output:**
```
Added watch: a1b2c3d4
Name: Job Listings
URL: https://example.com/jobs
Interval: 24 hours
```

**Behavior:**
- Fetches page immediately to establish baseline
- Stores content snapshot for future comparison
- Adds to watches.json

### watch list

List all watched pages.

```bash
web watch list [--json]
```

**Output:**
```
Watches (3):

[a1b2c3d4] Job Listings
  URL: https://example.com/jobs
  Interval: 24h | Last checked: 2 hours ago | Changes: 0

[b2c3d4e5] Documentation
  URL: https://docs.example.com/api
  Interval: 168h | Last checked: 3 days ago | Changes: 2

[c3d4e5f6] Price Tracker
  URL: https://shop.example.com/item/123
  Interval: 6h | Last checked: 1 hour ago | Changes: 5
```

### watch check

Check watched pages for changes.

```bash
web watch check [--id WATCH_ID] [--all]
```

**Arguments:**
- `--id` — Check specific watch (optional)
- `--all` — Check all watches regardless of interval (optional)

Without arguments, checks watches due based on their interval.

**Output (no changes):**
```
Checked 3 watches, no changes detected.
```

**Output (changes detected):**
```
Changes detected in 2 watches:

[a1b2c3d4] Job Listings
  3 new sections, 1 removed section

[c3d4e5f6] Price Tracker
  Content changed (diff: 15%)
```

**Behavior:**
- Fetches current content
- Compares against stored snapshot
- Updates snapshot if changed
- Returns change summary

### watch remove

Remove a page from the watch list.

```bash
web watch remove <watch_id>
```

**Output:**
```
Removed watch: a1b2c3d4 (Job Listings)
```

### watch show

Show details and recent changes for a watched page.

```bash
web watch show <watch_id> [--diff]
```

**Arguments:**
- `watch_id` — Watch ID (required)
- `--diff` — Show diff from last change

**Output:**
```
Watch: a1b2c3d4
Name: Job Listings
URL: https://example.com/jobs
Interval: 24 hours
Added: 2024-01-15
Last checked: 2024-01-20 14:30
Total checks: 12
Changes detected: 3

Recent changes:
  2024-01-20: 3 new sections
  2024-01-18: 1 section removed
  2024-01-16: Minor text changes
```

## Data Schemas

### watches.json

```json
{
  "watches": [
    {
      "id": "a1b2c3d4",
      "url": "https://example.com/jobs",
      "name": "Job Listings",
      "credentials_id": null,
      "check_interval_hours": 24,
      "added_at": "2024-01-15T10:00:00",
      "last_checked": "2024-01-20T14:30:00",
      "last_changed": "2024-01-20T14:30:00",
      "check_count": 12,
      "change_count": 3,
      "last_error": null,
      "error_count": 0
    }
  ]
}
```

The `credentials_id` field references a credential in `data/system/config.json` (see "Design for Future Credentials"). Initially always null.

### config.json

```json
{
  "default_check_interval_hours": 24,
  "min_check_interval_hours": 1,
  "max_check_interval_hours": 168,
  "snapshot_max_size_kb": 500,
  "user_agent": "Euno/1.0 (Web Skill)"
}
```

## Integration with Other Systems

### Memory Integration

When `watch check` detects changes, the agent should:
1. Create a short-term memory entry (type: `idea` or `thing`)
2. Include the watch name, URL, and change summary
3. Memory description enables proactive agent behavior

Example memory entry:
```json
{
  "type": "thing",
  "short_description": "Job Listings page changed: 3 new postings detected",
  "date_mentioned": "2024-01-20"
}
```

### Trigger Integration

Agents can subscribe to web watch checks via triggers in their config:

```json
{
  "triggers": [
    {
      "type": "schedule",
      "schedule": "0 9 * * *",
      "action": "skill:web:watch check"
    }
  ]
}
```

Or watches can be checked as part of a broader "morning routine" topic.

### Topic Integration

The `web save` command integrates with the core topic/asset system:
- Saved content becomes a topic asset
- Agent can reference it in future work on that topic
- Follows standard asset lifecycle (archived with topic)

## Implementation Notes

### Content Extraction

Uses `skills.common.extract_main_content()` which:
1. Removes script, style, nav, header, footer, aside elements
2. Looks for semantic containers: `<article>`, `<main>`
3. Falls back to common class patterns: `.post-content`, `.entry-content`, etc.
4. Last resort: `<body>` content

### Change Detection

Simple but effective approach:
1. Store plain text extraction (not HTML) to ignore markup changes
2. Compare using content hash for quick "changed/unchanged" check
3. For detailed diff, use line-based comparison
4. Report: sections added, sections removed, percentage changed

### Rate Limiting

Inherits from `skills.common.HTTPClient`:
- 1 second minimum between requests to same host
- Maximum 2 concurrent requests per host
- Configurable via `configure_rate_limiter()`

### Error Handling

- Network errors → log error, increment error_count, continue
- HTTP 4xx/5xx → log error, may indicate page moved/removed
- Extraction failures → return raw content with warning
- After 5 consecutive errors, warn user about watch health

## Example Agent Workflows

### Job Search Workflow

```
Agent: I'll help you track job postings. Let me set up monitoring.

> web watch add "https://jobs.example.com/search?q=python" --name "Python Jobs" --interval 12

Agent: I've set up monitoring for Python job listings. I'll check every 12 hours
and let you know when new positions are posted.

[Later, during morning routine...]

> web watch check

Agent: Good news! The Python Jobs page has 3 new postings since yesterday.
Would you like me to fetch the details?

> web fetch "https://jobs.example.com/posting/123"
```

### Reference Documentation Workflow

```
User: Save the React hooks documentation to my "Learning React" topic.

Agent: I'll fetch and save that documentation.

> web save "https://react.dev/reference/react/hooks" topic-abc123 --filename "hooks-reference.md"

Agent: Saved hooks-reference.md (45.2 KB) to your Learning React topic.
You can reference it anytime while working on that topic.
```

### Research Workflow

```
User: What does the Euno project README say about installation?

Agent: Let me check.

> web fetch "https://github.com/example/euno/blob/main/README.md"

Agent: According to the README, installation requires...
[Agent summarizes content, doesn't persist anywhere]
```

## Design for Future Credentials

Authentication is out of scope for initial implementation, but the design should accommodate it:

**Storage location:** `data/system/config.json` under a `credentials` key (not in skill-specific storage). Credentials are system-wide, not skill-specific.

**Planned schema:**
```json
{
  "credentials": {
    "sites": [
      {
        "id": "github",
        "pattern": "github.com/*",
        "auth_type": "bearer",
        "token_env": "GITHUB_TOKEN"
      },
      {
        "id": "internal-wiki",
        "pattern": "wiki.example.com/*",
        "auth_type": "basic",
        "username": "...",
        "password_env": "WIKI_PASSWORD"
      }
    ]
  }
}
```

**Implementation hooks:**
- `HTTPClient` already supports `set_basic_auth()` and `set_bearer_token()`
- Fetch functions should accept an optional `credentials_id` parameter (ignored for now)
- Watch entries should store `credentials_id` if the page requires auth

This allows adding credential lookup later without changing the command interface.

## Future Considerations

These are explicitly **out of scope** for the initial implementation but noted for future reference:

- **Site adapters**: Pluggable modules for better extraction from specific sites (HN, GitHub, etc.)
- **JavaScript rendering**: Currently only fetches static HTML
- **Robots.txt compliance**: Could add opt-in strict compliance mode
- **Caching**: Response caching to reduce redundant fetches
