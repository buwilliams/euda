# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Euno is a personal intelligence that learns to anticipate you: doing tasks for you, curating what helps you thrive, and expanding your horizons.

## Key References

- `docs/1_pitch.md` - Product vision
- `docs/3_system.md` - Entities, ontology, and lifecycle
- `spec/*.md` - Design rules for drift detection
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
uv run euno dev patterns user        # View discovered patterns
uv run euno dev prompt chat system   # View system prompt

# Test execution
uv run euno dev job chat "Test task" --dry-run   # See prompt without executing
uv run euno dev tool list_jobs '{"status": "todo"}'  # Execute tool directly

# Trigger behaviors manually
uv run euno dev reflect chat --consolidate   # Run only consolidate phase
uv run euno dev explore chat                 # Trigger exploration

# Live monitoring
uv run euno dev watch                        # Stream all system events
uv run euno dev trace <job_id>               # Show execution trace
```

Use `--json` for machine-readable output. See `spec/7_dev_cli.md` for full documentation.

## Project Structure

```
euno/
├── main.py                 # Entry point, CLI
├── src/
│   ├── manager.py          # Agent Manager - starts/stops all agents
│   ├── agent/              # Agent module (Identity + Cognition + Memory + Behavior)
│   │   ├── agent.py        # Main Agent class
│   │   ├── cognition/      # Agent cognition (reasoning + metacognition)
│   │   │   ├── reasoning/  # First-order thinking
│   │   │   │   └── planning.py  # Strategic planning
│   │   │   └── metacognition/   # Second-order thinking (self-regulation)
│   │   │       ├── regulation/  # Self-regulation
│   │   │       │   ├── tokens.py    # Token/cost awareness
│   │   │       │   ├── progress.py  # Stuck detection
│   │   │       │   └── config.py    # Configuration
│   │   │       └── consolidation/   # Self-improvement (memory/identity)
│   │   │           ├── consolidation.py  # Main Consolidation class
│   │   │           ├── append.py    # Lightweight extraction after chat
│   │   │           └── consolidate.py    # Heavy analysis on trigger
│   │   └── rlm/            # Recursive Language Model for memory access
│   ├── metacognition/      # Legacy metacognition (imports from agent/cognition)
│   ├── reflection/         # Legacy reflection (imports from agent/cognition)
│   ├── llms/               # LLM clients and tools
│   │   ├── base.py         # Unified LLM client
│   │   └── tools/          # All tools (registered with @tool decorator)
│   │       ├── data/       # Jobs, assets, memory tools
│   │       ├── agents/     # Agent introspection tools
│   │       ├── system/     # Config, notifications tools
│   │       └── integration/    # External integrations
│   └── web/
│       ├── app.py          # FastAPI application
│       └── routes/         # API endpoints
├── data/
│   ├── agents/             # Agent configs and state
│   │   └── {agent-id}/
│   │       ├── config.json
│   │       ├── identity.md
│   │       ├── memory/
│   │       │   ├── short-term.jsonl
│   │       │   └── long-term/{yyyy}/{yyyy-mm-dd}.md
│   │       └── state/conversation/{session-id}.md
│   ├── jobs/
│   │   ├── db.sqlite       # SQLite database (jobs + job_logs tables)
│   │   └── assets/         # Files per job
│   │       └── {job-id}/
│   └── system/
│       ├── config.json
│       └── logs/reflection/ # Reflection logs
├── spec/                   # Design rules for drift detection
│   ├── 1_agents.md
│   ├── 2_data.md
│   ├── 3_backend.md
│   └── 4_ux_ui.md
├── web/                    # Web UI
└── devops/                 # Deployment scripts
```

## Core Concepts

### Agents
An agent is: **Identity + Cognition + Memory + Behavior**

- **Identity** (`identity.md`): Purpose, values, voice, stable attractors, context
- **Cognition**: Reasoning (system prompts) + Metacognition (self-regulation, reflection)
- **Memory**: Short-term (90 days) + Long-term (permanent archive)
- **Behavior** (`config.json`): Tools + Triggers + Modes (90/10 exploration ratio)

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

### Jobs
Jobs replace projects and tasks. A single hierarchical structure:
- Stored in SQLite database (`data/jobs/db.sqlite`)
- Hierarchical via `parent_id` field
- States: `todo`, `completed`, `archived`
- Each job can have assets (files) in `data/jobs/assets/{job-id}/`
- Assets can be any file type; text/markdown files are viewable and editable in the UI

### Memory
Memory tracks what's on an agent's mind for anticipation (every agent has memory):
- Short-term: `data/agents/{id}/memory/short-term.jsonl` (90-day rolling)
- Long-term: `data/agents/{id}/memory/long-term/{yyyy}/{yyyy-mm-dd}.md` (year-based archive)
- Types: person, place, thing, goal, concern, idea, learning, behavior
- Entries expire after 90 days and archive to long-term memory

### Exploration
Exploration is scheduled discovery where agents research opportunities for the user:
- Creates suggestions aligned with the agent's purpose and user's interests
- Applies 90/10 principle: 90% grounded in user's goals, 10% novel exposure
- Configured per-agent in `config.json` under `exploration` key
- Creates `Trigger:exploration:{date}` jobs when triggered

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
     "enabled": true,
     "tools": ["list_jobs", "create_job", ...],
     "triggers": ["time:morning", "system:start"],
     "exploration": {
       "enabled": true,
       "trigger": "time:hour_04"
     },
     "consolidation": {
       "enabled": true,
       "trigger": "time:evening"
     }
   }
   ```
3. Create `identity.md` with the agent's identity and behavioral rules
4. Restart the application

No Python code needed for new agents.

## Adding a New Tool

1. Add function in `src/tools/` with `@tool` decorator:
   ```python
   @tool("my_tool", "Description of what it does")
   def my_tool(param: str) -> dict:
       return {"result": param}
   ```
2. Import in `src/tools/__init__.py`
3. Add tool name to agent configs that should use it

## API Endpoints

- `GET/POST /api/jobs` - List/create jobs
- `GET/PATCH /api/jobs/{id}` - Get/update job
- `POST /api/jobs/{id}/complete` - Complete job
- `GET /api/jobs/{id}/assets` - List job assets
- `GET/POST/DELETE /api/jobs/{id}/assets/{filename}` - Asset CRUD
- `GET/POST /api/chat` - Chat with agent
- `GET /api/agents` - List agents
- `GET/PATCH /api/agents/{id}/identity` - Agent identity
- `GET/PATCH /api/agents/{id}/config` - Agent config
- `GET/POST/DELETE /api/agents/{id}/memory/short-term` - Agent memory
- `GET /api/agents/{id}/monitoring` - Agent monitoring stats
- `POST /api/agents/{id}/reflection/trigger` - Trigger reflection
- `POST /api/agents/{id}/exploration/trigger` - Trigger exploration
- `GET /api/agents/{id}/patterns` - Agent's discovered patterns
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

Before submitting changes, review against `spec/*.md`:
- `spec/1_agents.md` — Agent behavior, job coordination, triggers, work cycles
- `spec/2_data.md` — Data structures, file paths, schemas
- `spec/3_backend.md` — Server, API, authentication, storage
- `spec/4_ux_ui.md` — User experience and interface patterns
- `spec/5_cli.md` — Command-line interface commands and behavior
- `spec/7_dev_cli.md` — Developer CLI for debugging and improving agents
- `spec/8_patterns.md` — Pattern discovery, storage, and integration
