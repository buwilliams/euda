# Euno Architecture

## Overview

Euno is built on two core abstractions: **Agents** and **Jobs**. Agents are autonomous entities that work on Jobs. The human user is also an agent—just with a different interface.

## Design Principles

1. **Agents are generic** - All agents share the same architecture: config + persona + tools + loop
2. **User as agent** - The human interacts through Web UI or CLI; agents interact through autonomous loops
3. **Jobs are hierarchical** - Any job can contain sub-jobs, enabling natural decomposition of work
4. **Simple storage** - Flat files for agents, user profile, and lifelog; SQLite for jobs (efficient querying)
5. **Capabilities over permissions** - What an agent can do is defined by which tools it has access to

## Personal Intelligence

To achieve true personal intelligence, every agent must understand the user. Every LLM API call includes the user's profile in the system prompt:

```
┌─────────────────────────────────┐
│         System Prompt           │
├─────────────────────────────────┤
│  1. Agent Persona               │  ← Who the agent is
│  2. User Profile                │  ← Who the user is
│  3. Conversation Context        │  ← Recent history
└─────────────────────────────────┘
```

This means every agent—whether it's handling tasks, curating content, or just chatting—knows the user's preferences, patterns, and values. The intelligence is personal because it's grounded in a real model of who the user is.

The **User Profile** (`data/user/user-profile.md`) is built and maintained by the Profiler agent, which examines the Lifelog to identify patterns, preferences, and behaviors over time.

### The Lifelog

The Lifelog is the raw record of the user's life—journals, conversations, reflections, and significant moments. It lives in `data/user/lifelog/` as daily markdown files:

```
data/user/lifelog/
├── 2026-01-01.md
├── 2026-01-02.md
└── ...
```

**Purpose:**
- Capture lived experience before interpretation
- Preserve human signal (emotions, decisions, struggles) with high fidelity
- Provide evidence for the Profiler to build the User Profile

**Who writes to it:**
- The **Archivist** agent processes incoming content and writes to the Lifelog
- The **Friend** agent may log meaningful conversations
- Users can write directly via the web UI or CLI

**Who reads it:**
- The **Profiler** examines the Lifelog to identify patterns and update the User Profile
- Any agent can read the Lifelog to understand recent context

The Lifelog is intentionally raw and unprocessed. The Archivist's job is to preserve, not interpret. Interpretation happens later when the Profiler extracts patterns into the User Profile.

### Default Agents

Euno includes seven default agents:

| Agent | Purpose |
|-------|---------|
| **Friend** | Primary conversational interface. Supports thinking and decision-making while respecting identity. |
| **Assistant** | Task-focused helper for managing jobs, organizing work, and tracking progress. |
| **Worker** | Autonomous task executor. Handles work while preserving user agency over commitments. |
| **Profiler** | Constructs the User Profile from Lifelog data. Focuses on observed behavior, not stated preferences. |
| **Curator** | Manages attention as a scarce resource. Surfaces opportunities at appropriate times. |
| **Archivist** | Preserves human signal with high fidelity. Writes to the Lifelog without interpretation. |
| **Adaptor** | Proposes system evolution based on user behavior. Refines agent personas to reduce friction. |

Each agent has a distinct persona defining its behavior, but all share the same architecture and access to the User Profile.

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
│   └── db.sqlite                       # SQLite database (jobs + job_logs tables)
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

### Job Storage (SQLite)

Jobs are stored in a SQLite database at `data/jobs/db.sqlite`. SQLite provides efficient querying while remaining a simple, portable single-file database.

**Schema:**

```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,              -- e.g., "job-abc123"
    name TEXT NOT NULL,
    parent_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'completed', 'archived')),
    created_at TEXT NOT NULL,         -- ISO 8601 timestamp
    updated_at TEXT NOT NULL,
    created_by TEXT NOT NULL DEFAULT 'user',
    description TEXT,
    due_date TEXT,
    someday INTEGER NOT NULL DEFAULT 0,  -- boolean flag
    completed_at TEXT,
    tags TEXT                         -- JSON array, e.g., '["research", "pricing"]'
);

CREATE TABLE job_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    timestamp TEXT NOT NULL,
    agent TEXT NOT NULL,              -- which agent performed the action
    action TEXT NOT NULL              -- what happened
);
```

**Design decisions:**

- **Logs in separate table** — Logs are append-only and can grow large. A separate table enables efficient inserts without rewriting the job row. Cascade delete ensures cleanup.
- **Tags as JSON text** — Tags are always read/written with the job. No need for a separate table or complex queries.
- **ISO 8601 timestamps** — Human-readable, sortable as strings, compatible with SQLite date functions.

**Indexes:**

```sql
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_parent_id ON jobs(parent_id);
CREATE INDEX idx_jobs_updated_at ON jobs(updated_at DESC);
CREATE INDEX idx_job_logs_job_id ON job_logs(job_id);
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

1. **Conversation Pruning** — Conversation files grow indefinitely. When/how to summarize old context?

2. **Asset Cleanup** — When a job is archived, what happens to its assets?
