# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Euno is a personal intelligence for human flourishing. It helps you grow into who you're meant to be—through purpose and meaning. It can do tasks, curate information, and anticipate your needs, but those capabilities serve a deeper mission: helping you thrive.

## Key References

- `docs/1_pitch.md` - Product vision
- `docs/4_system.md` - Entities, ontology, and lifecycle
- `specs/*.md` - Design rules for drift detection
- `main.py` - Entry point

## Setup

1. Create a `.env` file from the example:
   ```
   cp .env.example .env
   ```

2. Add your OpenAI API key to `.env`:
   ```
   OPENAI_API_KEY=your-actual-key
   ```

3. Install dependencies (requires [uv](https://docs.astral.sh/uv/)):
   ```
   uv sync
   ```

4. Run Euno:
   ```
   uv run euno start    # Web server + agents (run in background in Claude Code)
   uv run euno chat     # Interactive chat with an agent
   ```

**Important for Claude Code:** When starting Euno during development, run it as a background task so the conversation can continue while the server runs.

## Development and Testing

Use the dev CLI for testing agent internals:

```bash
uv run euno dev <command> [args] [--json]

# Inspect agent state
uv run euno dev memory chat          # View agent's memory
uv run euno dev identity chat        # View agent's identity
uv run euno dev prompt chat system   # View system prompt

# Test execution
uv run euno dev topic chat "Test task" --dry-run   # See prompt without executing

# Trigger behaviors manually
uv run euno dev reflect chat --consolidate   # Run only consolidate phase

# Live monitoring
uv run euno dev watch                        # Stream all system events
uv run euno dev trace <topic_id>               # Show execution trace
```

Use `--json` for machine-readable output. See `specs/7_dev_cli.md` for full documentation.

### Testing Plugins

```bash
# List available plugins
uv run euno plugin list

# Get help for a plugin
uv run euno plugin core --help
uv run euno plugin core topics --help

# Run plugin commands directly
uv run euno plugin core topics list
uv run euno plugin core topics create "Test topic"
uv run euno plugin core memory list
```

## Project Structure

```
euno/
├── main.py                 # Entry point, CLI
├── plugins/                # Plugin directory
│   ├── core/               # Core Euno functionality
│   │   ├── cli.py          # Typer CLI entry point
│   │   └── commands/       # Command modules
│   │       ├── topics.py   # Topic management
│   │       ├── assets.py   # Asset operations
│   │       ├── memory.py   # Memory operations
│   │       ├── identity.py # Identity management
│   │       ├── agents.py   # Agent management
│   │       └── ...
│   ├── nextcloud/          # Nextcloud integration
│   ├── speech/             # Text-to-speech
│   └── mastodon/           # Mastodon integration
├── src/
│   ├── plugins/            # Plugin infrastructure
│   │   ├── discovery.py    # Scan plugins/, validate
│   │   ├── executor.py     # Run CLI via subprocess
│   │   ├── usage.py        # Extract --help text
│   │   ├── context.py      # Build env vars
│   │   └── tools.py        # 3 meta-tools for LLM
│   ├── agent/              # Agent module (Identity + Cognition + Memory + Behavior)
│   │   ├── agent.py        # Main Agent class
│   │   ├── manager.py      # Agent Manager
│   │   └── cognition/      # Reasoning + Metacognition
│   ├── tools/              # Business logic (called by plugins)
│   │   ├── data/           # Topics, assets, memory
│   │   ├── agents/         # Agent operations
│   │   ├── system/         # Config, notifications
│   │   └── integration/    # External integrations
│   ├── llms/               # LLM clients
│   └── web/                # FastAPI application
├── data/
│   ├── agents/             # Agent configs and state
│   ├── topics/             # SQLite database + assets
│   └── system/             # System config and logs
├── specs/                  # Design rules for drift detection
├── web/                    # Web UI
└── devops/                 # Deployment scripts
```

## Core Concepts

### Plugins

Agents interact with Euno through **plugins** - CLI-based extensions that provide capabilities. The LLM uses three meta-tools:

- `list_plugins` - Discover available plugins
- `plugin_usage(plugin)` - Get help for a plugin
- `execute_plugin(plugin, command)` - Run a plugin command

Built-in plugins:
- **core**: Topics, memory, agents, identity, consolidation, dates
- **nextcloud**: Files, calendar, deck integration
- **speech**: Text-to-speech
- **mastodon**: Social media posts

See `specs/8_plugins.md` for full plugin documentation.

### Agents
An agent is: **Identity + Cognition + Memory + Behavior**

- **Identity** (`identity.md`): Purpose, values, voice, stable attractors, context
- **Cognition**: Reasoning (system prompts) + Metacognition (self-regulation, reflection)
- **Memory**: Short-term (90 days) + Long-term (permanent archive)
- **Behavior** (`config.json`): Plugins + Triggers

### Metacognition
Metacognition is the agent's self-regulation and self-improvement system:
Metacognition has two aspects:

**Self-Regulation** (in `agent/cognition/metacognition/regulation/`):
- **Token Awareness**: Pre-call estimation, post-call recording, per-agent budgets with auto-pause
- **Agent States**: `enabled`, `disabled`, `paused` (paused requires manual intervention)
- **Progress**: Detect stuck patterns and break loops
- **Incidents**: Threshold breaches logged and surfaced via API

**Self-Improvement** (in `agent/cognition/metacognition/consolidation/`):
- **Consolidation**: Process memories, update identity (formerly called Reflection)
- **Append phase**: Lightweight extraction after each conversation
- **Consolidate phase**: Heavy analysis on daily trigger

System-wide defaults in `data/system/config.json` under `metacognition` key.

### Topics
Topics are the primary unit of work. A single hierarchical structure:
- Stored in SQLite database (`data/topics/db.sqlite`)
- Hierarchical via `parent_id` field
- States: `todo`, `working`, `done`, `error`, `archived`
- Each topic can have assets (files) in `data/topics/assets/{topic-id}/`
- Assets can be any file type; text/markdown files are viewable and editable in the UI

### Memory
Memory tracks what's on an agent's mind for anticipation (every agent has memory):
- Short-term: `data/agents/{id}/memory/short-term.jsonl` (90-day rolling)
- Long-term: `data/agents/{id}/memory/long-term/{yyyy}/{yyyy-mm-dd}.md` (year-based archive)
- Types: person, place, thing, goal, concern, idea, learning, behavior
- Entries expire after 90 days and archive to long-term memory

### Consolidation
Consolidation is a metacognition capability (self-improvement) that manages memory and identity:
- **Append phase**: Lightweight extraction after each conversation (adds to short-term memory)
- **Consolidate phase**: Heavy analysis on daily trigger (graduates memories, updates identity)
- Activation configured per-agent: `consolidation.trigger` in `config.json`
- Logs stored in `data/system/logs/consolidation/`

### User as Agent
The user is conceptually an agent too - just with a different interface (Web UI/CLI vs autonomous loop).

## Adding a New Agent

1. Create directory: `data/agents/{agent-id}/`
2. Create `config.json`:
   ```json
   {
     "id": "myagent",
     "name": "My Agent",
     "state": "enabled",
     "excluded_plugins": [],
     "triggers": [],
     "consolidation": {
       "enabled": true,
       "trigger": "time:evening"
     }
   }
   ```
3. Create `identity.md` with the agent's identity and behavioral rules
4. Restart the application

No Python code needed for new agents.

## Adding a New Plugin

1. Create directory: `plugins/{name}/`
2. Create `cli.py`:
   ```python
   """My plugin description."""
   import typer

   app = typer.Typer(name="myplugin", help="My plugin help")

   @app.command()
   def mycommand():
       """Command description."""
       print("Output")

   def main():
       app()

   if __name__ == "__main__":
       main()
   ```
3. Plugins are auto-discovered on next invocation

See `specs/8_plugins.md` for full documentation.

## API Endpoints

- `GET/POST /api/topics` - List/create topics
- `GET/PATCH /api/topics/{id}` - Get/update topic
- `POST /api/topics/{id}/complete` - Complete topic
- `GET /api/topics/{id}/assets` - List topic assets
- `GET/POST/DELETE /api/topics/{id}/assets/{filename}` - Asset CRUD
- `GET/POST /api/chat` - Chat with agent
- `GET /api/agents` - List agents
- `GET/PATCH /api/agents/{id}/identity` - Agent identity
- `GET/PATCH /api/agents/{id}/config` - Agent config
- `GET/POST/DELETE /api/agents/{id}/memory/short-term` - Agent memory
- `GET /api/agents/{id}/monitoring` - Agent monitoring stats
- `POST /api/agents/{id}/reflection/trigger` - Trigger reflection
- `GET/PATCH /api/user/identity` - User identity
- `GET/POST /api/user/memory/long-term` - Long-term memory entries
- `GET/POST/DELETE /api/user/memory` - Memory items
- `POST /api/fresh-start` - Reset user data with backup
- `GET /api/backups` - List/restore backups

## Development Philosophy

Build for yourself first, not "other people." This is not a solution looking for a problem.

- Build the best agent for the creator's own daily use
- Refine through lived experience, not hypothetical users
- Features get prioritized by real need, rough edges smoothed by real annoyance

## Checking for Drift

Before submitting changes, review against `specs/*.md`:
- `specs/1_agents.md` — Agent behavior, topic coordination, triggers, work cycles
- `specs/2_data.md` — Data structures, file paths, schemas
- `specs/3_backend.md` — Server, API, authentication, storage
- `specs/4_ux_ui.md` — User experience and interface patterns
- `specs/5_cli.md` — Command-line interface commands and behavior
- `specs/7_dev_cli.md` — Developer CLI for debugging and improving agents
- `specs/8_plugins.md` — Plugin architecture and commands
