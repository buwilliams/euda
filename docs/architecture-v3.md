# Euno Architecture v3 - Unified Agent System

## Overview

A radically simplified architecture where everything is either an **Agent** or a **Job**. Agents are configurable entities (human or autonomous) that work on Jobs. Jobs are hierarchical units of work with assets and logs.

## Core Principles

1. **Agents are generic** - No hardcoded agent types. All agents are config + tools + loop.
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
    └── config.json                     # API keys, global settings
```

## Agents

### Agent Definition

An agent is defined by three things:
1. **Config** (`config.json`) - operational parameters
2. **Persona** (`{agent}-persona.md`) - identity and behavior
3. **Tools** - list of tool names the agent can use

### Agent Config Schema

```json
{
  "id": "archivist",
  "name": "The Archivist",
  "enabled": true,
  "tools": ["read_file", "write_file", "create_job", "complete_job"],
  "sleep_minutes": 5
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier |
| `name` | string | Display name |
| `enabled` | boolean | Whether agent runs |
| `tools` | string[] | Tools this agent can use |
| `sleep_minutes` | number | Sleep between work cycles (0 = continuous) |

### Agent Types

**Autonomous Agents** - Run in a loop managed by Agent Manager:
- Wake up, check for work, do work, sleep, repeat
- Decide internally when they're "done" for a cycle
- Examples: Archivist, Curator, Worker

**User Agent** - Special case:
- Interacts via Web UI or CLI
- Same underlying architecture, different interface
- Conversation history stored same as other agents

### Agent Lifecycle

```
┌─────────────────────────────────────────────────┐
│                 Agent Manager                    │
│  - Starts all enabled agents on app startup     │
│  - Monitors agent health                        │
│  - Restarts failed agents                       │
│  - Handles graceful shutdown                    │
└─────────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐
   │ Agent A │   │ Agent B │   │ Agent C │
   │  Loop   │   │  Loop   │   │  Loop   │
   └─────────┘   └─────────┘   └─────────┘
        │             │             │
        ▼             ▼             ▼
   ┌─────────────────────────────────────┐
   │           Work Cycle                 │
   │  1. Check for relevant jobs         │
   │  2. Do work (use tools)             │
   │  3. Update job state                │
   │  4. Sleep for configured duration   │
   │  5. Repeat                          │
   └─────────────────────────────────────┘
```

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
    {
      "timestamp": "2025-01-15T10:30:00Z",
      "agent": "user",
      "action": "created"
    },
    {
      "timestamp": "2025-01-15T14:22:00Z",
      "agent": "worker",
      "action": "Started research on competitor A"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier |
| `name` | string | Job title |
| `parent_id` | string? | Parent job ID (null for top-level) |
| `status` | enum | `todo`, `completed`, `archived` |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last modification |
| `created_by` | string | Agent ID that created it |
| `description` | string? | Detailed description |
| `due_date` | datetime? | Optional deadline |
| `tags` | string[] | Categorization |
| `log` | array | Activity history |

### Job States

| State | Description |
|-------|-------------|
| `todo` | Active, needs work |
| `completed` | Finished successfully |
| `archived` | No longer relevant, preserved for history |

### Job Hierarchy

Jobs form a tree via `parent_id`:

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

### Job Assets

Assets are stored in `data/assets/{job-id}/`:
- Any file type (images, documents, data files)
- Referenced from job description or log entries
- Organized by job for easy cleanup

### Job Handoff

Jobs move between agents implicitly:
1. Agent A finishes work on a job
2. Agent A updates job log: "Completed research, ready for review"
3. Agent B (in its next cycle) sees the job needs attention
4. Agent B picks it up based on its persona/purpose

No explicit assignment - agents decide based on their identity what jobs they should work on.

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

### Tool Registration

Tools are Python functions registered with the system:

```python
@tool(name="create_job", description="Create a new job")
def create_job(name: str, description: str = None, parent_id: str = None) -> dict:
    """Create a new job and return its details."""
    ...
```

## Agent Manager

### Responsibilities

1. **Startup** - Load all agent configs, start enabled agents
2. **Monitoring** - Track agent health, detect failures
3. **Restart** - Automatically restart crashed agents
4. **Shutdown** - Gracefully stop all agents on app exit
5. **Hot Reload** - Detect config changes, restart affected agents

### Implementation

```python
class AgentManager:
    def __init__(self):
        self.agents = {}  # agent_id -> AgentRunner

    async def start_all(self):
        """Start all enabled agents."""
        configs = load_all_agent_configs()
        for config in configs:
            if config["enabled"]:
                self.agents[config["id"]] = AgentRunner(config)
                await self.agents[config["id"]].start()

    async def shutdown(self):
        """Gracefully stop all agents."""
        for agent in self.agents.values():
            await agent.stop()
```

### Agent Runner

Each agent runs in its own async task:

```python
class AgentRunner:
    def __init__(self, config):
        self.config = config
        self.running = False

    async def start(self):
        self.running = True
        while self.running:
            await self.work_cycle()
            await asyncio.sleep(self.config["sleep_minutes"] * 60)

    async def work_cycle(self):
        # 1. Build context (persona + memory + recent conversation)
        # 2. Check for relevant jobs
        # 3. Call LLM with tools
        # 4. Execute tool calls
        # 5. Update state
        ...
```

## Web Server

### API Endpoints

**Jobs:**
- `GET /api/jobs` - List jobs (with query params)
- `GET /api/jobs/{id}` - Get job
- `POST /api/jobs` - Create job
- `PATCH /api/jobs/{id}` - Update job
- `DELETE /api/jobs/{id}` - Archive job

**Agents:**
- `GET /api/agents` - List agents
- `GET /api/agents/{id}` - Get agent details
- `PATCH /api/agents/{id}` - Update agent config
- `POST /api/agents/{id}/enable` - Enable agent
- `POST /api/agents/{id}/disable` - Disable agent

**Chat:**
- `POST /api/chat` - Send message, get response
- `GET /api/chat/history` - Get conversation history

**User:**
- `GET /api/user/profile` - Get user profile
- `PATCH /api/user/profile` - Update profile
- `GET /api/user/lifelog` - Get lifelog entries

**Assets:**
- `GET /api/jobs/{id}/assets` - List job assets
- `GET /api/jobs/{id}/assets/{filename}` - Get asset
- `POST /api/jobs/{id}/assets` - Upload asset
- `DELETE /api/jobs/{id}/assets/{filename}` - Delete asset

### Static UI

Static files served from `static/`:
- Single-page app
- Communicates via API
- Real-time updates via SSE or polling

## Source Code Structure

```
src/
├── main.py                 # Entry point, CLI
├── manager.py              # Agent Manager
├── agent.py                # Generic Agent Runner
├── tools/
│   ├── __init__.py         # Tool registry
│   ├── jobs.py             # Job CRUD tools
│   ├── assets.py           # Asset management tools
│   ├── user.py             # User profile/lifelog tools
│   ├── agents.py           # Agent introspection tools
│   └── system.py           # System/notification tools
└── web/
    ├── app.py              # FastAPI application
    └── routes/
        ├── jobs.py
        ├── agents.py
        ├── chat.py
        └── user.py
```

## Example: Creating a New Agent

1. Create directory: `data/agents/researcher/`

2. Create config (`config.json`):
```json
{
  "id": "researcher",
  "name": "The Researcher",
  "enabled": true,
  "tools": ["list_jobs", "get_job", "update_job", "add_job_log", "write_asset"],
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

## Constraints
- Always cite sources
- Flag uncertainty
- Don't make things up
```

4. Restart Agent Manager (or it hot-reloads)

5. Agent starts working on research-tagged jobs

## Migration Path

### From Current Architecture

1. Archive current code to `old-architecture/`
2. Create new `src/` with minimal implementation
3. Migrate data:
   - Existing projects → Jobs
   - Existing tasks → Child Jobs
   - Agent personas → `data/agents/{id}/{id}-persona.md`
   - Conversation history → `data/agents/{id}/state/conversation/`
   - User profile → `data/user/user-profile.md`
   - Lifelog → `data/user/lifelog/`

### Preserved Components

- `static/` - Web UI (works with new API)
- `devops/` - Deployment scripts
- `.env` - Configuration

## Open Questions

1. **Job Indexing** - With flat files, how do we efficiently query "all jobs where status=todo"? Options:
   - Scan all files (fine for <1000 jobs)
   - Maintain an index file (`jobs-index.json`)
   - SQLite for job metadata only

2. **Conversation Pruning** - Conversation files grow forever. When/how to summarize old context?

3. **Asset Cleanup** - When a job is archived, what happens to its assets?

4. **Agent Creation via Chat** - What's the UX for a user creating a new agent through conversation?
