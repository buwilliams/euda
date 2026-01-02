# Euno Architecture - Unified Agent System

## Overview

A radically simplified architecture where everything is either an **Agent** or a **Job**. Agents are configurable entities (human or autonomous) that work on Jobs. Jobs are hierarchical units of work with assets and logs.

## Core Principles

1. **Agents are generic** - No hardcoded agent types. All agents are config + persona + tools + loop.
2. **User is an agent** - The human user is just another agent with a different interface (Web UI/CLI vs autonomous loop).
3. **Jobs replace projects and tasks** - A single hierarchical structure with arbitrary depth.
4. **Flat files everywhere** - Human-readable, inspectable, version-controllable.
5. **No permissions, only capabilities** - What an agent can do is controlled by which tools it has access to.

## Data Structure

```
data/
├── agents/
│   └── {agent-id}/
│       ├── config.json                 # tools, sleep timer, enabled
│       ├── {agent-id}-persona.md       # identity/system prompt
│       ├── logs/
│       │   └── {date}.json             # activity logs by date
│       └── state/
│           ├── memory.json             # persistent agent memory
│           └── conversation/
│               └── {date}.md           # conversation history by date
├── jobs/
│   └── {job-id}.json                   # flat structure with parent_id
├── assets/
│   └── {job-id}/                       # assets organized by job
│       └── {filename}
├── user/
│   ├── user-profile.md                 # user preferences and patterns
│   └── lifelog/
│       └── {date}.md                   # daily journals
└── system/
    └── config.json                     # system-wide settings
```

## System Configuration

System-wide settings are stored in `data/system/config.json`:

```json
{
  "version": "3.0.0",
  "initialized": true,
  "agents": {
    "max_work_iterations": 20,
    "min_sleep_seconds": 60
  }
}
```

| Setting | Description |
|---------|-------------|
| `agents.max_work_iterations` | Safety limit for autonomous work loop (prevents runaway agents) |
| `agents.min_sleep_seconds` | Minimum sleep between work cycles (prevents tight loops) |

## Agents

### What Is An Agent?

At its core, an agent is simply:
- **A persona** (system prompt defining identity)
- **A context** (conversation history)
- **Tools** (functions the agent can call)
- **A loop** (process input → call LLM → handle tools → repeat until done)

That's it. No magic. The LLM receives the conversation context, decides what to do, optionally calls tools, and returns a response. The agent continues working until it decides it's done.

### Agent Definition

An agent is defined by:
1. **Config** (`config.json`) - operational parameters
2. **Persona** (`{agent}-persona.md`) - identity and behavior
3. **Tools** - list of tool names the agent can use

### Agent Config Schema

```json
{
  "id": "archivist",
  "name": "The Archivist",
  "enabled": true,
  "tools": ["read_file", "write_file", "create_job", "complete_job", "done_working"],
  "sleep_minutes": 5
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier |
| `name` | string | Display name |
| `enabled` | boolean | Whether agent runs |
| `tools` | string[] | Tools this agent can use |
| `sleep_minutes` | number | Sleep between work cycles |

### Autonomous Work Cycle

Each agent runs in its own **thread** (not async task) to prevent blocking:

```
┌─────────────────────────────────────────────────────────────┐
│                     Agent Work Cycle                         │
├─────────────────────────────────────────────────────────────┤
│  1. Wake up                                                  │
│  2. Check for jobs (list_jobs)                              │
│  3. If no jobs → log "no_jobs" → sleep                      │
│  4. If jobs exist:                                          │
│     ┌──────────────────────────────────────────────────┐    │
│     │  Autonomous Loop (until done_working called)      │    │
│     │  ├── Send prompt to LLM                          │    │
│     │  ├── Execute any tool calls                      │    │
│     │  ├── Check if agent called done_working          │    │
│     │  └── If not done, continue with follow-up prompt │    │
│     └──────────────────────────────────────────────────┘    │
│  5. Log sleep duration and wake time                        │
│  6. Sleep for configured duration                           │
│  7. Log wake event                                          │
│  8. Repeat from step 2                                      │
└─────────────────────────────────────────────────────────────┘
```

The agent decides when it's done by calling the `done_working` tool. This makes agents truly autonomous—they work until they determine there's nothing left to do.

### The done_working Tool

Every agent should have access to the `done_working` tool:

```python
done_working(summary: str = "") -> dict
```

When called:
- Sets a flag that ends the autonomous loop
- Logs the completion with optional summary
- Agent proceeds to sleep phase

Safety limit: If an agent doesn't call `done_working` after `max_work_iterations` (default 20), the loop ends automatically.

### Agent Logging

Each agent maintains activity logs in `logs/{date}.json`:

```json
[
  {"timestamp": "2026-01-02T04:30:00", "event": "work_cycle_start"},
  {"timestamp": "2026-01-02T04:30:01", "event": "work_cycle_jobs_found", "details": {"count": 3}},
  {"timestamp": "2026-01-02T04:30:01", "event": "work_iteration", "details": {"iteration": 1}},
  {"timestamp": "2026-01-02T04:30:01", "event": "chat_start", "details": {"message_length": 245}},
  {"timestamp": "2026-01-02T04:30:03", "event": "llm_response", "details": {"stop_reason": "tool_use", "usage": {"input": 1200, "output": 85}}},
  {"timestamp": "2026-01-02T04:30:03", "event": "tool_call", "details": {"tool": "list_jobs", "input": {"status": "todo"}}},
  {"timestamp": "2026-01-02T04:30:03", "event": "tool_result", "details": {"tool": "list_jobs", "success": true}},
  {"timestamp": "2026-01-02T04:30:05", "event": "llm_response", "details": {"stop_reason": "tool_use", "usage": {"input": 1500, "output": 45}}},
  {"timestamp": "2026-01-02T04:30:05", "event": "tool_call", "details": {"tool": "done_working", "input": {"summary": "No jobs match my role"}}},
  {"timestamp": "2026-01-02T04:30:05", "event": "done_working", "details": {"summary": "No jobs match my role"}},
  {"timestamp": "2026-01-02T04:30:07", "event": "chat_end", "details": {"response_length": 150}},
  {"timestamp": "2026-01-02T04:30:07", "event": "work_cycle_end", "details": {"reason": "done_working", "iterations": 1}},
  {"timestamp": "2026-01-02T04:30:07", "event": "sleep", "details": {"duration_seconds": 300, "wake_at": "2026-01-02T04:35:07"}},
  {"timestamp": "2026-01-02T04:35:07", "event": "wake"}
]
```

Log events:
| Event | Description |
|-------|-------------|
| `work_cycle_start` | Agent woke up and started checking for work |
| `work_cycle_end` | Work cycle finished (reason: `done_working`, `no_jobs`, or `max_iterations`) |
| `work_iteration` | Started a new iteration of the autonomous loop |
| `chat_start` / `chat_end` | LLM conversation boundaries |
| `llm_response` | Response received from LLM (includes token usage) |
| `tool_call` | Agent called a tool |
| `tool_result` | Tool execution completed |
| `done_working` | Agent signaled completion |
| `sleep` | Agent going to sleep (includes duration and wake time) |
| `wake` | Agent woke from sleep |
| `error` | An error occurred |

### Agent Memory & Conversation

Each agent maintains its own:

**Conversation History** (`state/conversation/{date}.md`):
- Daily markdown files
- Full context preserved across sessions
- Used to maintain continuity

**Memory** (`state/memory.json`):
- Persistent facts the agent has learned
- Survives restarts
- Agent-specific knowledge

## Agent Manager

The Agent Manager starts each agent in its own thread:

```
┌─────────────────────────────────────────────────┐
│                 Agent Manager                    │
│  - Loads all agent configs on startup           │
│  - Starts each enabled agent in its own thread  │
│  - Monitors thread health                       │
│  - Handles graceful shutdown                    │
└─────────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐
   │ Thread  │   │ Thread  │   │ Thread  │
   │ Agent A │   │ Agent B │   │ Agent C │
   └─────────┘   └─────────┘   └─────────┘
```

Each thread runs independently—one agent's work cannot block another.

## Jobs

### Job Concept

Jobs unify the old "projects" and "tasks" concepts:
- A Job can contain other Jobs (via `parent_id`)
- Jobs have assets (files, images, documents)
- Jobs track state and history
- All agents can see all jobs (visibility is universal)

### Job Schema

```json
{
  "id": "job-abc123",
  "name": "Research competitor pricing",
  "parent_id": null,
  "status": "todo",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T14:22:00Z",
  "created_by": "user",
  "description": "Gather pricing data from top 5 competitors",
  "due_date": null,
  "tags": ["research", "pricing"],
  "log": [
    {"timestamp": "2025-01-15T10:30:00Z", "agent": "user", "action": "created"},
    {"timestamp": "2025-01-15T14:22:00Z", "agent": "worker", "action": "Started research on competitor A"}
  ]
}
```

### Job States

| State | Description |
|-------|-------------|
| `todo` | Active, needs work |
| `completed` | Finished successfully |
| `archived` | No longer relevant, preserved for history |

### Job Assets

Assets are stored in `data/assets/{job-id}/`:
- Any file type (images, documents, data files)
- Referenced from job description or log entries
- Organized by job for easy cleanup

## Tools

### Tool Philosophy

- Tools are generic functions available to agents
- An agent's capabilities are defined by its tool list
- Tools are the only way agents interact with the system

### Core Tool Categories

**Job Tools:**
- `list_jobs` - Query jobs (with filters)
- `get_job` - Get job details
- `create_job` - Create new job
- `update_job` - Modify job
- `complete_job` - Mark job completed
- `archive_job` - Archive job
- `add_job_log` - Add log entry

**Asset Tools:**
- `list_assets` - List assets for a job
- `read_asset` - Read asset content
- `write_asset` - Create/update asset
- `delete_asset` - Remove asset

**User Tools:**
- `get_user_profile` - Read user profile
- `update_user_profile` - Modify user profile
- `read_lifelog` - Access lifelog entries
- `write_lifelog` - Add lifelog entry

**Agent Tools:**
- `list_agents` - List all agents
- `get_agent_memory` - Read agent memory
- `update_agent_memory` - Store in agent memory

**System Tools:**
- `get_config` - Read system config
- `send_notification` - Notify user
- `done_working` - Signal work completion (for autonomous loop)

### Tool Registration

Tools are Python functions registered with the `@tool` decorator:

```python
@tool("create_job", "Create a new job")
def create_job(name: str, description: str = None, parent_id: str = None) -> dict:
    """Create a new job and return its details."""
    ...
```

## Web Server

### API Routes

Routes are organized by domain:

```
src/web/routes/
├── auth.py      # /api/auth/* (login, logout, check)
├── chat.py      # /api/chat/* (messages, history, conversations)
├── system.py    # /api/* (health, about, settings, events)
├── jobs.py      # /api/jobs/*
├── agents.py    # /api/agents/*
└── user.py      # /api/user/*
```

### Real-Time Updates (SSE)

The web UI receives real-time updates via Server-Sent Events (SSE):

**Endpoint:** `GET /api/events`

```javascript
const eventSource = new EventSource('/api/events');

eventSource.addEventListener('init', (e) => {
  const data = JSON.parse(e.data);
  // Initial state: { jobs: [...] }
});

eventSource.addEventListener('ping', (e) => {
  // Keep-alive ping every 30 seconds
});
```

SSE is preferred over polling because:
- Single persistent connection (not repeated requests)
- Server pushes updates immediately
- Lower latency, less overhead
- Automatic reconnection on disconnect

### Static UI

Static files served from `static/`:
- Single-page app
- Communicates via API
- Real-time updates via SSE

## Source Code Structure

```
src/
├── main.py                 # Entry point, CLI
├── manager.py              # Agent Manager (thread-based)
├── agent.py                # Generic Agent
├── auth.py                 # Password/session authentication
├── tools/
│   ├── __init__.py         # Tool registry
│   ├── jobs.py             # Job CRUD tools
│   ├── assets.py           # Asset management tools
│   ├── user.py             # User profile/lifelog tools
│   ├── agents.py           # Agent introspection tools
│   └── system.py           # System/notification/done_working tools
└── web/
    ├── app.py              # FastAPI application (router config)
    └── routes/
        ├── jobs.py         # /api/jobs/*
        ├── agents.py       # /api/agents/*
        ├── chat.py         # /api/chat/*
        ├── user.py         # /api/user/*
        ├── auth.py         # /api/auth/*
        └── system.py       # /api/* (health, about, etc.)
```

## Example: Creating a New Agent

1. Create directory: `data/agents/researcher/`

2. Create config (`config.json`):
```json
{
  "id": "researcher",
  "name": "The Researcher",
  "enabled": true,
  "tools": ["list_jobs", "get_job", "update_job", "add_job_log", "write_asset", "done_working"],
  "sleep_minutes": 10
}
```

3. Create persona (`researcher-persona.md`):
```markdown
# The Researcher

You are a research specialist. Your purpose is to gather information,
synthesize findings, and document research results.

## Behavior
- Look for jobs tagged with "research"
- Gather information from available sources
- Document findings as job assets
- Update job logs with progress
- Call done_working when finished or when no research jobs need attention

## Constraints
- Always cite sources
- Flag uncertainty
- Don't make things up
```

4. Restart the application

5. Agent starts working on research-tagged jobs

## Open Questions

1. **Job Indexing** - With flat files, how do we efficiently query "all jobs where status=todo"? Options:
   - Scan all files (fine for <1000 jobs)
   - Maintain an index file (`jobs-index.json`)
   - SQLite for job metadata only

2. **Conversation Pruning** - Conversation files grow forever. When/how to summarize old context?

3. **Asset Cleanup** - When a job is archived, what happens to its assets?
