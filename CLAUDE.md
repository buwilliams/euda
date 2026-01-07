# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Euno is a personal intelligence that learns to anticipate you: doing tasks for you, curating what helps you thrive, and expanding your horizons.

## Key References

- `docs/1_pitch.md` - Product vision
- `docs/3_anticipate.md` - How Profile + Memory enable anticipation
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
│   ├── agent.py            # Generic Agent - config + persona + tools + loop
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
│   │       ├── {agent}-persona.md
│   │       └── state/conversation/{session-id}.md
│   ├── jobs/
│   │   ├── db.sqlite       # SQLite database (jobs + job_logs tables)
│   │   └── assets/         # Files per job
│   │       └── {job-id}/
│   ├── user/
│   │   ├── user-profile.md
│   │   ├── memory.jsonl    # Memory items for anticipation
│   │   └── lifelog/{date}.md
│   └── system/
│       └── config.json
├── spec/                   # Design rules for drift detection
│   ├── 1_data.md
│   ├── 2_system.md
│   └── 3_user-experience.md
├── static/                 # Web UI
└── devops/                 # Deployment scripts
```

## Core Concepts

### Agents
An agent is: **config + persona + tools + triggers**

- Config (`config.json`): id, name, enabled, tools list, triggers
- Persona (`{agent}-persona.md`): System prompt defining behavior
- Tools: Functions the agent can call (controlled by config)
- Triggers: Events that wake the agent (e.g., `job:assigned`, `time:morning`)

### Jobs
Jobs replace projects and tasks. A single hierarchical structure:
- Stored in SQLite database (`data/jobs/db.sqlite`)
- Hierarchical via `parent_id` field
- States: `todo`, `completed`, `archived`
- Each job can have assets (files) in `data/jobs/assets/{job-id}/`
- Assets can be any file type; text/markdown files are viewable and editable in the UI

### Memory
Memory tracks what's on the user's mind for anticipation:
- Stored in `data/user/memory.jsonl`
- Types: person, place, thing, goal, concern, idea
- Entries expire after 90 days
- Included in every LLM system prompt

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
     "triggers": ["job:assigned", "time:morning"]
   }
   ```
3. Create `{agent-id}-persona.md` with the agent's identity
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

## Development Philosophy

Build for yourself first, not "other people." This is not a solution looking for a problem.

- Build the best agent for the creator's own daily use
- Refine through lived experience, not hypothetical users
- Features get prioritized by real need, rough edges smoothed by real annoyance

## Checking for Drift

Before submitting changes, review against `spec/*.md`:
- `spec/1_data.md` — Data structures, file paths, schemas
- `spec/2_system.md` — System behavior, agent rules, architecture
- `spec/3_user-experience.md` — UI patterns, interaction rules
