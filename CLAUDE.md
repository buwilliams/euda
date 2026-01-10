# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Euno is a personal intelligence that learns to anticipate you: doing tasks for you, curating what helps you thrive, and expanding your horizons.

## Key References

- `docs/1_pitch.md` - Product vision
- `docs/3_agents.md` - What agents are and how they work
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

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run Euno:
   ```
   python main.py start    # Web server + agents (run in background in Claude Code)
   python main.py chat     # Interactive chat with an agent
   ```

**Important for Claude Code:** When starting Euno during development, run it as a background task so the conversation can continue while the server runs.

## Project Structure

```
euno/
├── main.py                 # Entry point, CLI
├── src/
│   ├── manager.py          # Agent Manager - starts/stops all agents
│   ├── agent.py            # Generic Agent - config + profile + tools + synthesis
│   ├── synthesis/          # Memory and profile synthesis
│   │   ├── synthesis.py    # Main Synthesis class
│   │   ├── append.py       # Lightweight extraction after chat
│   │   ├── consolidate.py  # Heavy analysis on daily trigger
│   │   └── prompts.py      # LLM prompts for synthesis
│   ├── tools/              # All tools (registered with @tool decorator)
│   │   ├── jobs.py         # Job CRUD
│   │   ├── assets.py       # File attachments per job
│   │   ├── agents.py       # Agent introspection
│   │   ├── user.py         # Profile and lifelog
│   │   ├── memory.py       # Memory tracking for anticipation
│   │   └── system.py       # Config and notifications
│   └── web/
│       ├── app.py          # FastAPI application
│       └── routes/         # API endpoints
├── data/
│   ├── agents/             # Agent configs and state
│   │   └── {agent-id}/
│   │       ├── config.json
│   │       ├── profile.md
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
│       └── logs/synthesis/ # Synthesis logs
├── spec/                   # Design rules for drift detection
│   ├── 1_agents.md
│   ├── 2_data.md
│   ├── 3_backend.md
│   └── 4_ux_ui.md
├── static/                 # Web UI
└── devops/                 # Deployment scripts
```

## Core Concepts

### Agents
An agent is: **config + profile + tools + synthesis**

- Config (`config.json`): id, name, enabled, tools list, triggers, synthesis settings
- Profile (`profile.md`): Identity, behavioral rules, and learned patterns
- Tools: Functions the agent can call (controlled by config)
- Synthesis: Internal process that manages memory and updates profiles

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
- Types: person, place, thing, goal, concern, idea
- Entries expire after 90 days and archive to long-term memory

### Synthesis
Synthesis is an internal process each agent runs to manage memory and profiles:
- **Append phase**: Lightweight extraction after each conversation (adds to short-term memory)
- **Consolidate phase**: Heavy analysis on daily trigger (graduates memories, updates profile)
- Configured per-agent in `config.json` under `synthesis` key
- Logs stored in `data/system/logs/synthesis/`

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
     "synthesis": {
       "enabled": true,
       "append_enabled": true,
       "consolidate_trigger": "time:evening"
     }
   }
   ```
3. Create `profile.md` with the agent's identity and behavioral rules
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
- `GET/PATCH /api/user/profile` - User profile
- `GET/POST /api/user/lifelog` - Lifelog entries
- `GET/POST/DELETE /api/user/memory` - Memory items

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
