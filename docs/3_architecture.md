# Euno Architecture

## Overview

Euno is built on two core abstractions: **Agents** and **Jobs**. Agents are autonomous entities that work on Jobs. The human user is also an agent—just with a different interface.

## Design Principles

1. **Agents are generic** - All agents share the same architecture: config + persona + tools + loop
2. **User as agent** - The human interacts through Web UI or CLI; agents interact through autonomous loops
3. **Jobs are hierarchical** - Any job can contain sub-jobs, enabling natural decomposition of work
4. **Flat files** - All data is human-readable, inspectable, and version-controllable
5. **Capabilities over permissions** - What an agent can do is defined by which tools it has access to

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

Global settings live in `data/system/config.json`:

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
| `agents.max_work_iterations` | Safety limit for autonomous work loop |
| `agents.min_sleep_seconds` | Minimum sleep between work cycles |

## Agents

### What Is An Agent?

An agent is:
- **A persona** — system prompt defining identity and behavior
- **A context** — conversation history providing continuity
- **Tools** — functions the agent can call to interact with the system
- **A loop** — process input → call LLM → handle tools → repeat until done

The LLM receives context, decides what to do, optionally calls tools, and responds. The agent continues until it decides it's finished.

### Agent Definition

Each agent has:
1. **Config** (`config.json`) — operational parameters
2. **Persona** (`{agent}-persona.md`) — identity and behavior
3. **Tools** — list of tool names the agent can use

### Agent Config

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
| `sleep_minutes` | number | Sleep duration between work cycles |

### Autonomous Work Cycle

Each agent runs in its own thread:

```
┌─────────────────────────────────────────────────────────────┐
│                     Agent Work Cycle                         │
├─────────────────────────────────────────────────────────────┤
│  1. Wake up                                                  │
│  2. Check for jobs                                          │
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
│  8. Repeat                                                  │
└─────────────────────────────────────────────────────────────┘
```

The agent decides when it's done by calling `done_working`. This makes agents truly autonomous—they work until they determine there's nothing left to do.

### The done_working Tool

Every agent should have access to `done_working`:

```python
done_working(summary: str = "") -> dict
```

When called:
- Sets a flag that ends the autonomous loop
- Logs the completion with optional summary
- Agent proceeds to sleep

Safety: If an agent doesn't call `done_working` after `max_work_iterations`, the loop ends automatically.

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
  {"timestamp": "2026-01-02T04:30:05", "event": "done_working", "details": {"summary": "No jobs match my role"}},
  {"timestamp": "2026-01-02T04:30:07", "event": "work_cycle_end", "details": {"reason": "done_working", "iterations": 1}},
  {"timestamp": "2026-01-02T04:30:07", "event": "sleep", "details": {"duration_seconds": 300, "wake_at": "2026-01-02T04:35:07"}},
  {"timestamp": "2026-01-02T04:35:07", "event": "wake"}
]
```

| Event | Description |
|-------|-------------|
| `work_cycle_start` | Agent began checking for work |
| `work_cycle_end` | Work cycle finished |
| `work_iteration` | Started a new iteration of the autonomous loop |
| `chat_start` / `chat_end` | LLM conversation boundaries |
| `llm_response` | Response from LLM (includes token usage) |
| `tool_call` | Agent called a tool |
| `tool_result` | Tool execution completed |
| `done_working` | Agent signaled completion |
| `sleep` | Going to sleep (includes duration and wake time) |
| `wake` | Woke from sleep |
| `error` | An error occurred |

### Agent Memory & Conversation

Each agent maintains:

**Conversation History** (`state/conversation/{date}.md`):
- Daily markdown files
- Full context preserved across sessions
- Provides continuity

**Memory** (`state/memory.json`):
- Persistent facts the agent has learned
- Survives restarts
- Agent-specific knowledge

## Agent Manager

The Agent Manager orchestrates all agents:

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

### What Is A Job?

A job is a unit of work. Jobs can contain other jobs (via `parent_id`), enabling natural hierarchical decomposition:

```
Job: "Q1 Product Launch"
├── Job: "Marketing Materials"
│   ├── Job: "Write blog post"
│   └── Job: "Create social media assets"
├── Job: "Technical Prep"
│   ├── Job: "Performance testing"
│   └── Job: "Security audit"
└── Job: "Launch Day"
    └── Job: "Monitor metrics"
```

Jobs have:
- Assets (files, images, documents)
- Activity logs
- State tracking

All agents can see all jobs—visibility is universal.

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
    {"timestamp": "2025-01-15T14:22:00Z", "agent": "worker", "action": "Started research"}
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
- Organized by job for easy management

### Job Handoff

Jobs move between agents implicitly:
1. Agent A finishes work, updates job log
2. Agent B sees the job needs attention in its next cycle
3. Agent B picks it up based on its persona

No explicit assignment—agents decide based on their identity what jobs they should work on.

## Tools

### Philosophy

- Tools are the only way agents interact with the system
- An agent's capabilities are defined by its tool list
- Tools are generic functions available to any agent

### Tool Categories

**Job Tools:**
- `list_jobs` — Query jobs (with filters)
- `get_job` — Get job details
- `create_job` — Create new job
- `update_job` — Modify job
- `complete_job` — Mark job completed
- `archive_job` — Archive job
- `add_job_log` — Add log entry

**Asset Tools:**
- `list_assets` — List assets for a job
- `read_asset` — Read asset content
- `write_asset` — Create/update asset
- `delete_asset` — Remove asset

**User Tools:**
- `get_user_profile` — Read user profile
- `update_user_profile` — Modify user profile
- `read_lifelog` — Access lifelog entries
- `write_lifelog` — Add lifelog entry

**Agent Tools:**
- `list_agents` — List all agents
- `get_agent_memory` — Read agent memory
- `update_agent_memory` — Store in agent memory

**System Tools:**
- `get_config` — Read system config
- `send_notification` — Notify user
- `done_working` — Signal work completion

### Tool Registration

Tools are Python functions with the `@tool` decorator:

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

The web UI receives real-time updates via Server-Sent Events:

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

SSE advantages:
- Single persistent connection
- Server pushes updates immediately
- Lower latency than polling
- Automatic reconnection

### Static UI

Static files served from `static/`:
- Single-page application
- Communicates via REST API
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
    ├── app.py              # FastAPI application
    └── routes/
        ├── jobs.py
        ├── agents.py
        ├── chat.py
        ├── user.py
        ├── auth.py
        └── system.py
```

## Creating a New Agent

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
synthesize findings, and document results.

## Behavior
- Look for jobs tagged with "research"
- Gather information from available sources
- Document findings as job assets
- Update job logs with progress
- Call done_working when finished

## Constraints
- Always cite sources
- Flag uncertainty
- Don't fabricate information
```

4. Restart the application

5. Agent starts working on research-tagged jobs

## Open Questions

1. **Job Indexing** — With flat files, how do we efficiently query jobs? Options:
   - Scan all files (fine for <1000 jobs)
   - Maintain an index file
   - SQLite for metadata only

2. **Conversation Pruning** — Conversation files grow indefinitely. When/how to summarize old context?

3. **Asset Cleanup** — When a job is archived, what happens to its assets?
