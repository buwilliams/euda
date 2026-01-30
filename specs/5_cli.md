# CLI

Rules for the command-line interface.

## Entry Point

- Single entry point: `euno {command}`
- Default command is `help` if none specified
- Unknown commands show help and exit with code 1

## Commands

- `web` — Run web server (port 8000) with agents in background
- `chat [agent]` — Interactive chat with an agent (default: user)
- `skills` — Run skill commands
- `dev` — Developer tools for debugging agents
- `set-password` — Set access password for web UI (empty password disables auth)
- `remove-password` — Disable authentication
- `fresh-start` — Reset all user data while keeping configs

### Sync Commands

- `sync` — Full sync: stop server, sync code, sync data, restart server
- `sync --data-only` — Sync only data, skip code sync
- `sync --push` — Push local data to remote only
- `sync --pull` — Pull remote data to local only
- `sync --delete` — Delete files not on source (requires --push or --pull)
- `sync --dry-run` — Preview changes without applying
- `sync --no-backup` — Skip backup before sync
- `sync init [server]` — Initialize sync with remote server
- `sync status` — Show sync state and pending conflicts
- `sync conflicts` — Interactively walk through each conflict, prompting to keep local, keep remote, or skip
- `sync conflicts --non-interactive` — List unresolved conflicts without prompting
- `sync resolve <id> --keep-local|--keep-remote|--keep-newest` — Resolve a conflict

### Server Commands

- `server-setup` — Setup remote server (first time only)
- `server-remote` — SSH into remote server
- `server-remove` — Remove remote server

## web

- Validates config before starting
- Starts agents in background thread via AgentManager
- Runs uvicorn web server on 0.0.0.0:8000
- Custom signal handling closes SSE connections before shutdown

## chat

- Starts AgentManager in background thread (full platform running)
- Creates Agent instance for interactive REPL
- Supports any agent by ID (default: user)
- Handles budget exceeded gracefully
- Type 'quit', 'exit', or 'q' to end session

## skills

- `skills list` — List all available skills
- `skills <name> --help` — Show skill help
- `skills <name> <command> [args]` — Execute skill command

Skill commands replace direct CLI commands for topics, agents, memory, etc.

Examples:
```
euno skills core topics list
euno skills core agents list
euno skills core memory list
euno skills core store import ~/docs
```

See `specs/8_skills.md` for full skill documentation.

## sync

By default, sync performs full deployment:
1. Stops remote server (`systemctl stop euno`)
2. Syncs source code (local → remote, one-way with `--delete`)
3. Syncs data (bidirectional, non-destructive with conflict detection)
4. Restarts remote server (only if no conflicts)

Key behaviors:
- Uses `--checksum` for reliable file comparison across time zones
- Creates backups before applying changes (local backup for pull, remote for push)
- Topological sort ensures parent topics are imported before children
- When conflicts are detected, drops into interactive resolution by default (prompt per conflict: keep local, keep remote, or skip)
- Use `--non-interactive` to skip interactive resolution and list conflicts instead
- Use `--data-only` to skip code sync (steps 1, 2, 4)

Code sync excludes: `.git/`, `.venv/`, `data/`, `__pycache__/`, `*.pyc`, `.env`

Conflict resolution:
- `--keep-local` — Use local version
- `--keep-remote` — Use remote version
- `--keep-newest` — Use whichever has newer timestamp

## fresh-start

- Requires explicit confirmation (type 'yes')
- Deletes:
  - All agent memory (short-term and long-term)
  - All agent logs, state, and conversation history
  - All topics and topic assets
  - Cost tracking history
  - Consolidation logs
  - System trigger state
  - Password (if set)
  - Non-core agents (anything except chat, user, worker)
  - User uploads
- Resets: Core agent identities from `identity.template.md` templates
- Keeps: Agent configurations, system configuration
- Shows summary of deleted and reset items
