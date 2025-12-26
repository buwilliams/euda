# Design

Technical architecture and implementation spec for Euno.

## Philosophy

### Information Flow

When adding features or content, don't add directly. First examine the system's architecture and capabilities, then design the addition to align with them. If a capability is missing, consider carefully how to organize it alongside existing capabilities.

```
Architecture → Organization → Capabilities → Features
```

This hierarchy ensures coherent growth. Features serve capabilities, capabilities fit the organization, organization reflects architecture.

### Simplicity

Keep it simple. An agent is just:
- A context (list of messages)
- A loop (process input → call LLM → handle tools → repeat)
- Tools (JSON schemas describing functions)

As Thomas Ptacek notes: "Your wackiest idea will probably (1) work and (2) take 30 minutes to code."

---

## Core Patterns

### Agent Pattern

Every agent follows this pattern:

```python
def create_agent(persona_name, tools=[]):
    # Load core identity + persona-specific identity
    core = load_file("data/shared/identity/_core.identity.md")
    persona = load_file(f"data/shared/identity/{persona_name}.identity.md")

    context = []
    system_prompt = f"{core}\n\n{persona}"

    def process(input_content, handlers):
        context.append({"role": "user", "content": input_content})
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            system=system_prompt,
            tools=tools,
            messages=context
        )

        # Handle tool calls in a loop
        while has_tool_calls(response):
            results = execute_tools(response, handlers)
            context.append({"role": "assistant", "content": response.content})
            context.append({"role": "user", "content": results})
            response = client.messages.create(...)

        context.append({"role": "assistant", "content": response.content})
        return extract_text(response)

    return {"process": process, "clear_context": lambda: context.clear()}
```

### Autonomous Agent Pattern

Agents that run continuously:

```python
class AutonomousAgent:
    check_interval = 30  # seconds

    async def run(self):
        while self.running:
            if await self.check_work_needed():
                await self.do_work()
                self.send_signals()
            await asyncio.sleep(self.check_interval)

    def check_work_needed(self) -> bool:
        # Check signals, time windows, pending files, etc.
        pass

    def do_work(self):
        # Call agent.process() with appropriate prompt
        pass
```

### Sub-Agent Pattern

Spawn fresh context for complex tasks:

```python
def analyze_photo(photo_path):
    sub_agent = create_agent("ingestion", tools=[extract_exif, ocr_image])
    result = sub_agent["process"](f"Analyze: {photo_path}", handlers)
    return result  # Returns to parent, sub-agent context discarded
```

### Signal-Based Communication

Agents communicate via flat files, not direct calls:

```
data/shared/signals/
  logs_updated.signal        # Created by Ingestion, consumed by Summary
  summaries_updated.signal   # Created by Summary, consumed by Synthesis
  synthesis_updated.signal   # Created by Synthesis, consumed by World, Evolution
  proactive_gaps.json        # Created by Evolution, consumed by Attention
  agent_guidance.json        # Created by Evolution, consumed by all agents
```

Signal files contain a timestamp. Reading a signal deletes it (one-time trigger).

```python
def send_signal(name):
    Path(f"data/shared/signals/{name}.signal").write_text(datetime.now().isoformat())

def check_signal(name) -> bool:
    path = Path(f"data/shared/signals/{name}.signal")
    if path.exists():
        path.unlink()
        return True
    return False
```

### Proactive Behavior

The system proactively surfaces questions and guidance to help users configure and understand Euno:

**Evolution Agent Health Assessment:**
- Runs every 6 hours (or on first startup)
- Checks data completeness (biographical, relationships, values)
- Checks configuration (energy baseline, location)
- Identifies gaps with priorities (high/medium/low)
- Writes `proactive_gaps.json` for Attention to surface
- Writes `agent_guidance.json` to steer other agents

**Attention Agent Gap Surfacing:**
- Reads gaps signal, picks highest priority unsurfaced gap
- Surfaces as friendly notification ("Hey, I realized I don't know your name yet!")
- Tracks what's been asked in `surfaced.json` with cooldowns
- Respects cooldown periods (1 week for biographical, 1 day for energy)

**Agent Steering:**
- Evolution writes guidance signals for specific agents
- Interaction reads `learn_name_naturally` hint
- World reads `skip_location_opportunities` hint
- Agents adapt behavior without breaking

```json
// agent_guidance.json
{
  "guidance": {
    "interaction": { "learn_name_naturally": true },
    "world": { "skip_location_opportunities": true }
  }
}
```

**Tone:** Curious friend—warm and conversational, not corporate:
- "Hey, I realized I don't know your name yet!"
- "Quick thought—where are you based?"

### Identity System

Agents derive behavior from identity files loaded at startup:

```
data/shared/identity/
├── _core.identity.md      # Shared by all agents
├── ingestion.identity.md  # Archivist persona
├── interaction.identity.md # Caring Friend persona
└── ...
```

**Hierarchy:**
1. **Core Identity** — Shared purpose, values, boundaries (unchanging)
2. **Agent Persona** — Role-specific beliefs and behaviors
3. **Current Context** — Job to be done, relevant state

**Core identity contains:**
- Purpose (promote life, curate attention)
- Epistemic foundation (knowledge is conjecture)
- Shared beliefs (honesty builds trust)
- Universal boundaries (no harm, no manipulation)

**Each persona contains:**
- Who am I (self-concept)
- Purpose (why I exist)
- Beliefs (what I hold true, subject to revision)
- Behaviors (how I act)
- Learnings (discovered through experience)

**Identity Evolution:**

Agents can propose changes to their own identity:

```python
def propose_identity_change(agent_name, new_identity, rationale):
    proposal = {
        "agent": agent_name,
        "proposed": new_identity,
        "rationale": rationale,
        "status": "pending"
    }
    save_to(f"data/shared/evolution/{timestamp}.proposal.json", proposal)
    send_signal("identity_proposal")
```

User reviews proposals via `python main.py evolve`. Approved changes update the identity file.

---

## Agent Manager

Single process that spawns and monitors all agents:

```python
class AgentManager:
    async def start(self):
        self.agents = {
            "ingestion": asyncio.create_task(IngestionAgent().run()),
            "summary": asyncio.create_task(SummaryAgent().run()),
            # ...
        }

        while True:
            await self.health_check()
            await asyncio.sleep(60)

    async def health_check(self):
        for name, task in self.agents.items():
            if task.done():
                self.agents[name] = asyncio.create_task(self.restart(name))
```

---

## Directory Structure

Tools are organized by agent concern, data is organized by agent ownership.

```
euno/
├── main.py                     # Entry point
├── src/
│   ├── agents/
│   │   ├── base.py             # Agent factory, AutonomousAgent base
│   │   ├── ingestion.py        # The Archivist
│   │   ├── summary.py          # The Historian
│   │   ├── synthesis.py        # The Keeper (epistemic axioms at foundation)
│   │   ├── world.py            # The Scout
│   │   ├── attention.py        # The Curator
│   │   ├── interaction.py      # The Caring Friend
│   │   ├── worker.py           # The Executor
│   │   └── evolution.py        # The Evolver
│   │
│   ├── tools/                  # Organized by agent concern
│   │   ├── shared/             # Cross-agent tools
│   │   │   ├── log.py          # Life log read/write
│   │   │   ├── identity.py     # Agent identity evolution
│   │   │   ├── notifications.py
│   │   │   ├── agent_log.py    # Agent activity logging
│   │   │   └── guidance.py     # Agent steering from Evolution
│   │   ├── ingestion/          # Ingestion tools
│   │   │   ├── files.py
│   │   │   ├── classifier.py
│   │   │   ├── digest.py
│   │   │   ├── queue.py
│   │   │   ├── scorer.py
│   │   │   ├── token_budget.py
│   │   │   └── handlers/       # File type handlers
│   │   ├── synthesis/          # Synthesis tools (epistemic at foundation)
│   │   │   ├── epistemic.py    # Foundational: axioms, mental models, tools
│   │   │   ├── values.py       # Derived: current, phase, lifetime values
│   │   │   ├── behaviors.py    # Reveals: behavioral patterns
│   │   │   ├── context.py      # Supporting: biographical, relationships
│   │   │   ├── profile.py      # Consolidated profile
│   │   │   └── summary.py      # Summary tools
│   │   ├── world/              # World tools
│   │   │   ├── world.py
│   │   │   └── fetch.py
│   │   ├── attention/          # Attention tools
│   │   │   └── attention.py
│   │   ├── interaction/        # Interaction tools
│   │   │   ├── conversation.py
│   │   │   ├── conversation_history.py
│   │   │   └── cards.py
│   │   ├── worker/             # Worker tools
│   │   │   ├── task.py
│   │   │   ├── project.py
│   │   │   └── worker.py
│   │   └── evolution/          # Evolution tools
│   │       ├── evolution.py
│   │       └── health.py       # System health assessment
│   │
│   └── web/
│       └── app.py              # FastAPI server
│
└── data/                       # Agent-oriented data
    ├── shared/                 # Cross-agent resources
    │   ├── lifelog/            # Life log (written by ingestion, read by many)
    │   │   └── [yyyy]/
    │   │       ├── [yyyy-mm-dd].md
    │   │       └── _manifest.md
    │   ├── signals/            # Inter-agent triggers
    │   ├── identity/           # Agent identity files
    │   │   ├── _core.identity.md
    │   │   └── [agent].identity.md
    │   ├── evolution/          # Identity evolution proposals
    │   └── notifications/      # User notifications
    │
    ├── ingestion/              # Ingestion Agent data
    │   ├── state/              # state.json
    │   ├── config/             # config.json, processed_hashes.json
    │   ├── inbox/              # pending/, processing/, processed/, failed/, deferred/
    │   ├── queue/              # queue.json
    │   └── digests/            # {hash}.json files
    │
    ├── synthesis/              # Synthesis Agent data (epistemic at foundation)
    │   ├── state/              # state.json
    │   ├── epistemic/          # Foundational: axioms.md, mental_models.md, tools.md
    │   ├── values/             # Derived: current.values.md, phase.values.md, lifetime.values.md
    │   ├── behaviors/          # Reveals: patterns.md
    │   ├── context/            # Supporting: biographical.md, relationships.md
    │   └── derived/            # profile.md (consolidated view)
    │
    ├── world/                  # World Agent data
    │   ├── state/              # state.json
    │   └── opportunities/      # opportunities.json
    │
    ├── attention/              # Attention Agent data
    │   ├── state/              # state.json, surfaced.json (tracks asked questions)
    │   ├── config/             # config.json
    │   ├── prompts/            # proactive.md
    │   └── queue/              # surfacing_queue.json, energy logs
    │
    ├── interaction/            # Interaction Agent data
    │   ├── state/              # state.json
    │   └── conversations/      # session files
    │
    ├── worker/                 # Worker Agent data
    │   ├── state/              # state.json
    │   ├── tasks/              # queue.json, daily/, results/
    │   ├── projects/           # {id}.json files
    │   └── actions/            # pending/, completed/
    │
    └── evolution/              # Evolution Agent data
        ├── state/              # state.json
        ├── prompts/            # assess_health.md
        ├── output/             # capabilities.md
        └── logs/               # Evolution activity logs
```

---

## Agents Reference

| Agent | Check Interval | Triggers | Signals Out | Key Tools |
|-------|---------------|----------|-------------|-----------|
| Ingestion | 30s | `inbox_changed`, pending files | `logs_updated` | read_file, write_log, mark_processed |
| Summary | 5min | `logs_updated` | `summaries_updated` | read_log, write_summary |
| Synthesis | 10min | `summaries_updated` | `synthesis_updated` | read_summaries, write_epistemic, write_values |
| World | 1hr | `synthesis_updated`, 24hr timer | `opportunities_updated` | search_*, write_opportunity, get_guidance |
| Attention | 5min | time windows, `proactive_gaps` | `attention_delivered` | read_*, queue_notification, surface_gaps |
| Interaction | on-demand | user messages | — | read_*, write_log, update_biographical, get_guidance |
| Worker | 30s | pending tasks | `task_completed` | execute_task, store_result |
| Evolution | 30min | `synthesis_updated`, 6hr timer | `proactive_gaps`, `agent_guidance` | analyze_*, health_assessment, steer_agents |

### Large-Scale Ingestion Strategy

For processing large data volumes (72GB+), the Ingestion Agent uses a pre-processing pipeline:

```
File → Classifier → Extractor → Scorer → Budget Queue → AI Processing → Log
         ↓             ↓           ↓
      (local)      (local)    (local)
```

**Phases:**
1. **Classification** — Detect file type by magic bytes, route to handler
2. **Extraction** — Pull metadata locally (EXIF, PDF info, mbox headers)
3. **Scoring** — Relevance heuristics (recency, type, source)
4. **Budget Queue** — Daily token limit, priority ordering, rollover
5. **AI Processing** — Tiered models (Haiku → Sonnet → Vision)

**File Type Strategies:**

| Type | Local Extraction | AI Processing | Memory |
|------|-----------------|---------------|--------|
| Images | EXIF, dimensions | Vision for selected | Stream only |
| Videos | ffprobe, keyframes | Whisper for audio | Never load full |
| Audio | Duration, ID3 | Chunked Whisper | Stream chunks |
| PDFs | Metadata, TOC | Full <10 pages, summarize large | Page-by-page |
| mbox | Headers, threads | Summarize threads | Stream messages |
| Archives | List contents | Process extracted items | Temp extraction |

**Ignore Patterns:**
- Duplicates (SHA256 hash)
- System files (.DS_Store, Thumbs.db, caches)
- Spam/marketing emails
- Auto-generated content

**Token Budget:**

```python
class TokenBudget:
    def __init__(self, daily_limit=1_000_000):
        self.daily_limit = daily_limit
        self.used_today = 0
        self.last_reset = date.today()

    def can_spend(self, tokens: int) -> bool:
        self._maybe_reset()
        return self.used_today + tokens <= self.daily_limit

    def spend(self, tokens: int):
        self.used_today += tokens
```

**Temporal Detection Priority:**

File timestamps are unreliable. Determine actual time in this order:

1. **Content metadata** — EXIF DateTimeOriginal, PDF creation date
2. **Filename patterns** — `IMG_20240115_093042.jpg`, `Screenshot 2024-01-15`
3. **Content analysis** — Dates in text, receipt timestamps
4. **Cross-reference** — Match with existing log entries
5. **Contextual inference** — Email thread timing, file sequence
6. **File system timestamp** — Last resort, often wrong
7. **Ask user** — When confidence is too low

The `temporal_confidence` field in log entries tracks this: `high` (sources 1-2), `medium` (3-5), `low` (6-7).

### Worker Agent Delegation

The Worker Agent decides how to handle each task:

```
TASK arrives
    ↓
Is it a Learning task? ──YES──→ Prepare materials, surface to user
    ↓ NO
Is it User-Only? ──YES──→ Surface to user (cannot execute)
    ↓ NO                   (physical activity, creative work, decisions)
Is it High-Stakes? ──YES──→ Create pending action, request approval
    ↓ NO                    (external comms, calendar changes, financial)
Is it Read-Only/Research? ──YES──→ Execute autonomously, store result
    ↓ NO
Within rate limits? ──YES──→ Execute autonomously
    ↓ NO
Pause and notify (rate limit hit)
```

**Delegation strategies:**
- `agent_autonomous` — Execute without asking
- `requires_approval` — Create pending action, wait for user
- `user_only` — Cannot execute, surface to user
- `prepare_materials` — For learning tasks, curate but don't do

---

## Data Schemas

### Log Entry

```markdown
---
2024-12-22T09:30:00
source: manual
locality: home
type: note
temporal_confidence: high
temporal_source: explicit

[Content here]
---
```

### Project

```json
{
  "id": "project-xxx",
  "title": "Learn Spanish",
  "type": "learning",
  "status": "active",
  "priority": "high",
  "deadline": "2025-06-01",
  "milestones": [],
  "values_alignment": ["growth"]
}
```

### Task

```json
{
  "id": "task-xxx",
  "description": "Find conversation groups",
  "type": "research",
  "project_id": "project-xxx",
  "delegation": {
    "strategy": "agent_autonomous",
    "requires_approval": false
  },
  "scheduling": {
    "due_date": "2025-12-22",
    "energy_level": "medium"
  }
}
```

### Result

```json
{
  "id": "result-xxx",
  "task_id": "task-xxx",
  "summary": "Found 3 groups",
  "content": { "findings": [...] },
  "surfaced_to_user": false
}
```

### Notification

```json
{
  "id": "20251222_093000",
  "agent_name": "attention",
  "title": "Good morning",
  "message": "Here's what to focus on...",
  "type": "info",
  "action_prompt": "Tell me more",
  "priority": "normal",
  "status": "pending",
  "seen": false,
  "created_at": "2025-12-22T09:30:00"
}
```

Notifications are enriched by the web layer with additional UI fields:
- `panel`: "status" or "tasks" (where to display)
- `category`: "progress", "discovery", "reminder", "approval", "alert"
- `actions`: Available UI actions like "expand", "ask", "dismiss"

**Synthetic notifications** (like ingestion queue status) are generated at runtime from system state, not stored as files. They update in real-time as the underlying state changes.

### Digest (Ingestion)

```json
{
  "file_hash": "sha256:abc123",
  "original_path": "pending/photo.jpg",
  "file_type": "image/jpeg",
  "size_bytes": 2456789,
  "metadata": {
    "exif": { "date_taken": "2024-06-15T14:30:00" }
  },
  "relevance_score": 0.85,
  "estimated_tokens": 500,
  "processing_tier": "vision",
  "status": "queued"
}
```

### Conversation Session

```json
{
  "session_id": "abc123",
  "created": "2025-12-22T09:00:00",
  "messages": [
    {
      "timestamp": "2025-12-22T09:00:00",
      "user": "What should I focus on?",
      "assistant": "Based on your values..."
    }
  ]
}
```

---

## API Reference

```
POST /api/chat              # Send message, get response
POST /api/upload            # Upload file to inbox

GET  /api/logs/{year}/{date}
GET  /api/logs/search?q=
GET  /api/logs/recent?days=

GET  /api/values/current
GET  /api/values/phase
GET  /api/values/lifetime

GET  /api/tasks/today
POST /api/tasks
GET  /api/projects
POST /api/projects

GET  /api/notifications
POST /api/notifications/{id}/seen
POST /api/notifications/{id}/dismiss

GET  /api/events            # SSE stream for real-time updates

GET  /api/agents/status
GET  /api/health
```

### Real-Time Updates (SSE)

The `/api/events` endpoint provides Server-Sent Events for real-time updates:

| Event | Payload | Description |
|-------|---------|-------------|
| `init` | `{notifications, tasks}` | Initial state on connection |
| `notification_update` | notification object | New or updated notification |
| `notification_removed` | `{id}` | Notification dismissed/deleted |

The server watches:
- `data/shared/notifications/` for notification file changes
- `data/ingestion/inbox/` for queue status changes (synthetic notifications)

---

## User Interface

### Design Principles

**Attention is sacred.** Every element competes for attention. Therefore:

- **Empty is good** — A blank screen means "you're free, go live"
- **Push, don't pull** — System reaches out; user doesn't obsessively check
- **Chat is everything** — No separate screens, ask the friend anything

**Anti-patterns to avoid:**
- Cards/containers (create illusion of "content to consume")
- Grids of options (decision fatigue)
- Tabs (each demands attention)
- Stats/counts (gamification creates compulsion)
- Notification badges (anxiety triggers)

### Layout

```
┌─────────────────────────────────────┐
│  [logo] Euno                        │  ← Header
├─────────────────────────────────────┤
│  All quiet. Your attention is free. │  ← Activity feed
├─────────────────────────────────────┤
│                                     │
│  [friend message]                   │  ← Chat messages
│                    [user message]   │
│                                     │
│  [Talk to me...              ] Send │  ← Input
│                                     │
│  Try: "what are my values"          │  ← Hints
└─────────────────────────────────────┘
```

### Components

**Activity Feed:**
- Shows agent status in real-time
- "All quiet. Your attention is free." when idle
- "Ingestion working..." with pulsing dot when active
- Green dot for completed work
- Never leave user in limbo

**Chat:**
- User messages: black background, white text, right-aligned
- Friend messages: light gray background, black text, left-aligned
- Messages fade in with subtle slide-up animation
- "Thinking..." with animated dots during processing
- Input disabled while processing

**Hints:**
- Subtle suggestions below input
- Not buttons—conversation starters
- Click fills input field
- Examples: "what are my values", "any discoveries", "what did I log today"

**Side Panels:**
- Notifications panel (bell icon) — real-time agent activity
- Tasks panel (list icon) — user tasks and action items
- Slide in from right
- Updates via SSE (no polling)
- Notifications are expandable with details
- "Discuss" button fills chat with action_prompt and auto-submits
- "Dismiss" button removes notification (deletes file)
- Ingestion queue shows live status: pending, processing, failed counts

### Visual Style

- Typography-first: black text on white
- Generous whitespace
- No borders, shadows, gradients
- Logo as only graphical element
- Plain HTML with minimal CSS

---

## Running

```bash
# Web server with background agents (daily use)
python main.py serve

# Interactive chat only
python main.py chat

# Individual commands
python main.py morning      # Morning attention
python main.py evening      # Evening reflection
python main.py discover     # World discovery sweep
python main.py introspect   # System analysis
python main.py evolve       # Review identity proposals
```
