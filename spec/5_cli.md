# CLI

Rules for the command-line interface.

## Entry Point

- Single entry point: `python main.py {command}`
- Default command is `help` if none specified
- Unknown commands show help and exit with code 1

## Commands

- `start` — Run web server (port 8000) with agents in background
- `chat [agent]` — Interactive chat with an agent (default: friend)
- `agents` — List all agents with status, triggers, and last_ran
- `jobs` — List all jobs with status
- `points [name]` — Show contribution points, optionally filtered by name
- `set-password` — Set access password for web UI
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

## fresh-start

- Requires explicit confirmation (type 'yes')
- Deletes: lifelog, profile, memory, costs, jobs, assets, agent logs/state, system state, password
- Keeps: agent configs, agent personas, system config
- Shows summary of deleted items
