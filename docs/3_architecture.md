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
- The **Friend** agent logs meaningful user conversations (not autonomous work cycles)
- Users can write directly via the web UI or CLI

**Who reads it:**
- The **Profiler** examines the Lifelog to identify patterns and update the User Profile
- Any agent can read the Lifelog to understand recent context

The Lifelog is intentionally raw and unprocessed. The Archivist's job is to preserve, not interpret. Interpretation happens later when the Profiler extracts patterns into the User Profile.

### Default Agents

Euno includes six default agents:

| Agent | Purpose |
|-------|---------|
| **Friend** | Primary conversational interface. Supports thinking and decision-making while respecting identity. |
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
│       ├── config.json                 # tools, triggers, enabled
│       ├── {agent-id}-persona.md       # identity/system prompt
│       ├── logs/
│       │   └── {date}.json             # activity logs by date
│       └── state/
│           ├── memory.json             # persistent agent memory
│           └── conversation/
│               └── {session-id}.md     # conversation history by session
├── jobs/
│   ├── db.sqlite                       # SQLite database (jobs + job_logs tables)
│   └── assets/
│       └── {job-id}/                   # assets organized by job
│           └── {filename}
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
    "max_work_iterations": 20
  },
  "schedules": {
    "morning": "08:00",
    "evening": "18:00",
    "hourly": "every_hour"
  }
}
```

| Setting | Description |
|---------|-------------|
| `agents.max_work_iterations` | Safety limit for autonomous work loop |
| `schedules` | Named time schedules that emit `time:{name}` events |

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
  "triggers": ["job:assigned", "time:morning"]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier |
| `name` | string | Display name |
| `enabled` | boolean | Whether agent runs |
| `tools` | string[] | Tools this agent can use |
| `triggers` | string[] | Events that wake this agent (see Event System) |

### Event-Driven Work Cycle

Each agent runs in its own thread, waiting for trigger events:

```
┌─────────────────────────────────────────────────────────────┐
│                   Agent Work Cycle                           │
├─────────────────────────────────────────────────────────────┤
│  1. Wait for trigger event (from subscribed triggers)       │
│  2. Wake on event (e.g., job:assigned, time:morning)        │
│  3. Check for jobs that need attention                      │
│  4. If jobs exist:                                          │
│     ┌──────────────────────────────────────────────────┐    │
│     │  Autonomous Loop (until done_working called)      │    │
│     │  ├── Send prompt to LLM with trigger context      │    │
│     │  ├── Execute any tool calls                       │    │
│     │  ├── Check if agent called done_working           │    │
│     │  └── If not done, continue with follow-up prompt  │    │
│     └──────────────────────────────────────────────────┘    │
│  5. Return to waiting for next trigger                      │
└─────────────────────────────────────────────────────────────┘
```

Agents are purely event-driven—they only wake when a subscribed event fires. No polling or sleeping. The agent decides when it's done by calling `done_working`.

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
  {"timestamp": "2026-01-02T04:30:00", "event": "triggered", "details": {"event": {"event": "job:assigned", "data": {"job_id": "job-abc123"}}}},
  {"timestamp": "2026-01-02T04:30:00", "event": "work_cycle_start", "details": {"trigger": {"event": "job:assigned"}}},
  {"timestamp": "2026-01-02T04:30:01", "event": "work_cycle_jobs_found", "details": {"count": 3}},
  {"timestamp": "2026-01-02T04:30:01", "event": "work_iteration", "details": {"iteration": 1}},
  {"timestamp": "2026-01-02T04:30:01", "event": "chat_start", "details": {"message_length": 245}},
  {"timestamp": "2026-01-02T04:30:03", "event": "llm_response", "details": {"stop_reason": "tool_use", "usage": {"input": 1200, "output": 85}}},
  {"timestamp": "2026-01-02T04:30:03", "event": "tool_call", "details": {"tool": "list_jobs", "input": {"status": "todo"}}},
  {"timestamp": "2026-01-02T04:30:03", "event": "tool_result", "details": {"tool": "list_jobs", "success": true}},
  {"timestamp": "2026-01-02T04:30:05", "event": "done_working", "details": {"summary": "No jobs match my role"}},
  {"timestamp": "2026-01-02T04:30:07", "event": "work_cycle_end", "details": {"reason": "done_working", "iterations": 1}}
]
```

| Event | Description |
|-------|-------------|
| `triggered` | Agent woke due to an event |
| `work_cycle_start` | Agent began checking for work |
| `work_cycle_end` | Work cycle finished |
| `work_iteration` | Started a new iteration of the autonomous loop |
| `chat_start` / `chat_end` | LLM conversation boundaries |
| `llm_response` | Response from LLM (includes token usage) |
| `tool_call` | Agent called a tool |
| `tool_result` | Tool execution completed |
| `done_working` | Agent signaled completion |
| `error` | An error occurred |

### Agent Memory & Conversation

Each agent maintains:

**Conversation History** (`state/conversation/{session-id}.md`):
- Session-based markdown files (format: `YYYY-MM-DD_HHMMSS`)
- Each "New Chat" creates a new session
- Full context preserved within a session
- Multiple conversations per day supported
- Legacy date-only files (`YYYY-MM-DD.md`) still supported

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

## Event System

The event system enables agents to react to changes in the system without polling.

### Event Format

Events follow the pattern `{type}:{event}`:

| Event | Emitted When | Scope |
|-------|--------------|-------|
| `job:created` | New job created | Broadcast |
| `job:assigned` | Agent assigned to job | Scoped to agent |
| `job:unassigned` | Agent removed from job | Scoped to agent |
| `job:completed` | Job marked complete | Scoped to assignees |
| `job:archived` | Job archived | Scoped to assignees |
| `lifelog:new` | Lifelog entry added | Broadcast |
| `chat:message` | User sends chat message | Broadcast |
| `time:{schedule}` | Scheduled time reached | Broadcast |

### Scoped vs Broadcast Events

- **Broadcast events** wake all agents subscribed to that event type
- **Scoped events** only wake the specific agent they're targeted to

For example, `job:assigned` is scoped—when you assign a job to the worker agent, only the worker receives the event, not all agents subscribed to `job:assigned`.

### Time Scheduler

The manager runs a background time scheduler that emits `time:{name}` events based on the schedules in system config:

```json
{
  "schedules": {
    "morning": "08:00",
    "evening": "18:00",
    "hourly": "every_hour"
  }
}
```

- Exact times (e.g., `"08:00"`) fire once at that minute
- `"every_hour"` fires at minute 0 of every hour

### Default Agent Triggers

| Agent | Triggers |
|-------|----------|
| worker | `job:assigned`, `time:morning` |
| friend | `chat:message` |
| archivist | `job:assigned`, `time:morning` |
| profiler | `lifelog:new`, `time:evening` |
| curator | `time:morning` |
| adaptor | `time:evening` |

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
    tags TEXT,                        -- JSON array, e.g., '["research", "pricing"]'
    assignees TEXT,                   -- JSON array of agent IDs, e.g., '["worker", "archivist"]'
    in_progress_by TEXT               -- agent ID currently working on this job
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

Assets are stored in `data/jobs/assets/{job-id}/`:
- Any file type (images, documents, data files)
- Text and markdown files are viewable and editable in the UI
- Agents should create ONE comprehensive asset per job (not many fragments)
- Referenced from job description or log entries

### Job Assignment

Jobs can be explicitly assigned to agents via the `assignees` field:

```json
{
  "id": "job-abc123",
  "name": "Research competitors",
  "assignees": ["worker", "archivist"],
  "in_progress_by": "worker"
}
```

**How assignment works:**
1. Jobs can have multiple assignees (agents responsible for the job)
2. When assigned, the agent receives a `job:assigned` event and wakes immediately
3. An agent can claim exclusive work on a job via `in_progress_by`
4. Agents can self-assign using `assign_agent` or `claim_job` tools

**Claim vs Assign:**
- **Assignees** — Which agents are responsible for the job (multiple allowed)
- **in_progress_by** — Which agent is actively working right now (exclusive)

This prevents duplicate work when multiple agents could handle the same job.

### Job Handoff

Jobs can move between agents either implicitly or explicitly:

**Implicit (persona-based):**
1. Agent A finishes work, updates job log
2. Agent B sees the job needs attention when triggered
3. Agent B picks it up based on its persona

**Explicit (assignment-based):**
1. Job is assigned to specific agent(s)
2. Assigned agents receive `job:assigned` event
3. Agent claims job and works on it

## Tools

### Philosophy

- Tools are the only way agents interact with the system
- An agent's capabilities are defined by its tool list
- Tools are generic functions available to any agent

### Tool Categories

**Job Tools:**
- `list_jobs` — Query jobs (with filters for status, parent, tag, assignee)
- `get_job` — Get job details
- `create_job` — Create new job
- `update_job` — Modify job
- `complete_job` — Mark job completed
- `archive_job` — Archive job
- `add_job_log` — Add log entry
- `assign_agent` — Assign an agent to a job (emits `job:assigned`)
- `unassign_agent` — Remove agent from job (emits `job:unassigned`)
- `claim_job` — Claim exclusive work on a job
- `release_job` — Release a claimed job

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
├── events.py               # Event bus for agent triggers
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
  "triggers": ["job:assigned", "time:morning"]
}
```

3. Create persona (`researcher-persona.md`):
```markdown
# The Researcher

You are a research specialist. Your purpose is to gather information,
synthesize findings, and document results.

## Behavior
- Look for jobs assigned to you or tagged with "research"
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

5. Agent wakes when assigned jobs or at morning schedule

## Open Questions

1. **Conversation Pruning** — Conversation files grow indefinitely. When/how to summarize old context?

2. **Asset Cleanup** — When a job is archived, what happens to its assets?
