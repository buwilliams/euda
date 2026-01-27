# CLI

Rules for the command-line interface.

## Entry Point

- Single entry point: `uv run euno {command}`
- Default command is `help` if none specified
- Unknown commands show help and exit with code 1

## Commands

- `web` — Run web server (port 8000) with agents in background
- `chat [agent]` — Interactive chat with an agent (default: user)
- `plugin` — Run plugin commands
- `dev` — Developer tools for debugging agents
- `points [name]` — Show contribution points, optionally filtered by name
- `set-password` — Set access password for web UI (empty password disables auth)
- `remove-password` — Disable authentication
- `fresh-start` — Reset all user data while keeping configs

### Server Commands

- `server-deploy` — Deploy to remote server
- `server-pull` — Pull data from remote server
- `server-push` — Push data to remote server
- `server-push-agents` — Push agent configs to remote server
- `server-remote` — SSH into remote server
- `server-setup` — Setup remote server
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

## plugin

- `plugin list` — List all available plugins
- `plugin <name> --help` — Show plugin help
- `plugin <name> <command> [args]` — Execute plugin command

Plugin commands replace direct CLI commands for topics, agents, memory, etc.

Examples:
```
euno plugin core topics list
euno plugin core agents list
euno plugin core memory list
euno plugin core store import ~/docs
euno plugin scaffold plugin weather -d "Weather data"
```

See `specs/8_plugins.md` for full plugin documentation.

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
