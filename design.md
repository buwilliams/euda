# Design

Technical architecture and implementation spec for me·an·dus.

## Philosophy

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
    core = load_file("data/agents/identity/_core.identity.md")
    persona = load_file(f"data/agents/identity/{persona_name}.identity.md")

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
data/agents/signals/
  logs_updated.signal      # Created by Ingestion, consumed by Summary
  summaries_updated.signal # Created by Summary, consumed by Values
  values_updated.signal    # Created by Values, consumed by World
```

Signal files contain a timestamp. Reading a signal deletes it (one-time trigger).

```python
def send_signal(name):
    Path(f"data/agents/signals/{name}.signal").write_text(datetime.now().isoformat())

def check_signal(name) -> bool:
    path = Path(f"data/agents/signals/{name}.signal")
    if path.exists():
        path.unlink()
        return True
    return False
```

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

```
meandus/
├── main.py                     # Entry point
├── src/
│   ├── agents/
│   │   ├── base.py             # Agent factory, AutonomousAgent base
│   │   ├── ingestion.py
│   │   ├── summary.py
│   │   ├── values.py
│   │   ├── world.py
│   │   ├── attention.py
│   │   ├── interaction.py
│   │   ├── worker.py
│   │   └── introspection.py
│   ├── tools/
│   │   ├── log.py              # Life log read/write
│   │   ├── files.py            # File processing
│   │   ├── tasks.py            # Project/task management
│   │   ├── notifications.py
│   │   └── introspection.py
│   └── web/
│       └── app.py              # FastAPI server
│
└── data/
    ├── inbox/
    │   ├── pending/            # Files awaiting processing
    │   ├── processing/         # Currently being processed
    │   ├── processed/          # Successfully processed
    │   ├── failed/             # Failed (with .reason.txt)
    │   ├── deferred/           # Low-priority, waiting for budget
    │   └── metadata/           # Extracted digests
    │
    ├── log/
    │   └── [yyyy]/
    │       ├── [yyyy-mm-dd].md # Daily entries
    │       ├── _manifest.md    # Source tracking
    │       └── _summary.md     # Yearly distillation
    │
    ├── agents/
    │   ├── identity/
    │   │   ├── _core.identity.md
    │   │   └── [agent].identity.md
    │   ├── state/              # Persisted agent state (JSON)
    │   ├── signals/            # Inter-agent triggers
    │   └── introspection/
    │       └── capabilities.md
    │
    ├── tasks/
    │   ├── queue.json          # Master task queue
    │   ├── projects/
    │   ├── daily/
    │   └── results/
    │
    ├── values/
    │   ├── current.values.md
    │   ├── phase.values.md
    │   └── lifetime.values.md
    │
    ├── conversations/
    │   ├── sessions/
    │   └── daily/
    │
    └── notifications/
```

---

## Agents Reference

| Agent | Check Interval | Triggers | Signals Out | Key Tools |
|-------|---------------|----------|-------------|-----------|
| Ingestion | 30s | `inbox_changed`, pending files | `logs_updated` | read_file, write_log, mark_processed |
| Summary | 5min | `logs_updated` | `summaries_updated` | read_log, write_summary |
| Values | 10min | `summaries_updated` | `values_updated` | read_summaries, write_values |
| World | 1hr | `values_updated`, 24hr timer | `opportunities_updated` | search_*, write_opportunity |
| Attention | 5min | time windows (7-9am, 9-11pm) | `attention_delivered` | read_*, queue_notification |
| Interaction | on-demand | user messages | — | read_*, write_log, manage_tasks |
| Worker | 30s | pending tasks | `task_completed` | execute_task, store_result |
| Introspection | 30min | `identity_evolved` | `introspection_updated` | analyze_*, save_capabilities |

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
  "status": "pending"
}
```

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

GET  /api/agents/status
GET  /api/health
```

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
