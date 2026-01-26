# CLI

Rules for the command-line interface.

## Entry Point

- Single entry point: `uv run euno {command}`
- Default command is `help` if none specified
- Unknown commands show help and exit with code 1

## Commands

- `start` — Run web server (port 8000) with agents in background
- `chat [agent]` — Interactive chat with an agent (default: chat)
- `agents [name] [action]` — List agents or perform agent actions
- `topics` — List all topics with status
- `store <path>` — Import files into long-term memory
- `points [name]` — Show contribution points, optionally filtered by name
- `set-password` — Set access password for web UI (empty password disables auth)
- `remove-password` — Disable authentication
- `fresh-start` — Reset all user data while keeping configs

## start

- Validates config before starting
- Starts agents in background thread via AgentManager
- Runs uvicorn web server on 0.0.0.0:8000
- Custom signal handling closes SSE connections before shutdown

## chat

- Creates standalone Agent instance (not managed by AgentManager)
- Supports any agent by ID
- Handles budget exceeded gracefully
- Type 'quit', 'exit', or 'q' to end session

## agents

- `agents` — List all agents with status, triggers, and last_ran
- `agents [name]` — Show only the specified agent
- `agents [name] enable` — Enable the agent (updates config.json)
- `agents [name] disable` — Disable the agent (updates config.json)
- `agents [name] logs` — Show last 50 log entries from most recent log file
- `agents help` — Show available actions

## store

- `store <path>` — Import files into long-term memory
- `store <path> --dry-run` — Show what would be processed without creating topic
- `store <path> --force` — Reprocess files even if already imported
- `store --clear-manifest` — Clear legacy processing history

Processing flow:
1. Load files from path (supports .txt, .md, .json, .yaml, .csv, .log, .rst, .org)
2. Check for duplicates via topic tags (store:hash:{sha256})
3. Create `Store:ingest:{timestamp}` topic with files as assets
4. Chat agent processes topic, extracts dates, writes to long-term memory
5. Topic completion marks content as processed

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
