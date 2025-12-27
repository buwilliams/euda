# Architecture

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
    core = load_file("data/shared/state/identity/_core.identity.md")
    persona = load_file(f"data/shared/state/identity/{persona_name}.identity.md")

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
data/shared/state/signals/
  logs_updated.signal        # Created by Ingestion, consumed by Summary
  summaries_updated.signal   # Created by Summary, consumed by Synthesis
  synthesis_updated.signal   # Created by Synthesis, consumed by World, Evolution
  proactive_gaps.json        # Created by Evolution, consumed by Attention
  agent_guidance.json        # Created by Evolution, consumed by all agents
```

Signal files contain a timestamp. Reading a signal deletes it (one-time trigger).

```python
def send_signal(name):
    Path(f"data/shared/state/signals/{name}.signal").write_text(datetime.now().isoformat())

def check_signal(name) -> bool:
    path = Path(f"data/shared/state/signals/{name}.signal")
    if path.exists():
        path.unlink()
        return True
    return False
```

### Hash-Based Change Detection

Signals alone can cause redundant work—an agent might receive a signal but the underlying data hasn't actually changed since its last run. Agents use content hashes to verify changes before processing:

```python
# Each agent tracks what version of input data it last processed
def check_work_needed(self) -> bool:
    if self.check_signal("summaries_updated"):
        # Signal received, but verify data actually changed
        if self._have_summaries_changed():
            return True
        self.logger.debug("Signal received but content unchanged - skipping")
    return False

def _have_summaries_changed(self) -> bool:
    current_hash = compute_files_hash(summary_files)
    cached_hash = load_cached_hash(PROCESSED_SUMMARIES_HASH_FILE)
    return cached_hash is None or current_hash != cached_hash

def do_work(self):
    # ... do the work ...
    # Save hash so we know what we processed
    save_cached_hash(PROCESSED_SUMMARIES_HASH_FILE, current_hash)
```

**Hash file locations** (each agent tracks its own "last processed" version):

```
data/shared/state/lifelog/{year}/_summary.hash    # Summary Agent: logs hash for this year
data/synthesis/state/processed_summaries.hash     # Synthesis Agent: summaries it last processed
data/evolution/state/processed_synthesis.hash     # Evolution Agent: synthesis it last processed
data/world/state/processed_profile.hash           # World Agent: profile it last processed
data/attention/state/patterns.cache.json          # Attention Agent: cached pattern detection
```

**Why per-agent tracking?** Each agent independently tracks what *it* has processed. If the Synthesis Agent processes the summaries, the Evolution Agent still needs to know whether *it* has processed the resulting synthesis. Shared hashes wouldn't work—each downstream agent needs its own record.

**Utility module:** `src/tools/shared/content_hash.py` provides:
- `compute_file_hash()`, `compute_directory_hash()`, `compute_files_hash()`
- `load_cached_hash()`, `save_cached_hash()`
- `has_content_changed()`, `has_files_changed()`

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
data/shared/state/identity/
├── _core.identity.md        # Shared ontology for all agents
├── ingestion.identity.md    # The Archivist
├── summary.identity.md      # The Historian
├── synthesis.identity.md    # The Keeper
├── world.identity.md        # The Scout
├── attention.identity.md    # The Curator
├── interaction.identity.md  # The Caring Friend
├── worker.identity.md       # The Executor
└── evolution.identity.md    # The Evolver
```

**Hierarchy:**
1. **Core Identity** — Shared ontology, operating principles, canonical definitions
2. **Agent Persona** — Role-specific purpose, constraints, and output contracts
3. **Current Context** — Job to be done, relevant state

**Core identity contains:**
- Who Am I (caring friend, collaborative second mind, not authority or servant)
- Purpose (support eudaimonia—a life that holds together over time)
- Core Beliefs (fallibility, asymmetry of knowledge, human change, non-manipulation)
- What I Will Do / Will Not Do (behavioral commitments)
- Canonical Definitions (promotion of life, identity constraint, value, belief, failure mode, resistance)
- Advocacy Constraint (treat resistance as information, not opposition)
- Epistemic Foundation (promotion of life as bedrock)
- Identity Evolution (when and how agents can propose changes)

**Each persona contains:**
- Who Am I (persona self-concept, e.g., "The Archivist")
- Purpose (why this agent exists)
- Canonical/Core Definitions (role-specific terminology)
- Core Beliefs or Behavioral Rules/Constraints (what guides action)
- What I Track / Tools (inputs and capabilities)
- Output Contract (what this agent delivers)

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
    save_to(f"data/shared/state/evolution/{timestamp}.proposal.json", proposal)
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
│   │   ├── synthesis.py        # The Keeper (predictive identity model)
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
│   │   │   ├── guidance.py     # Agent steering from Evolution
│   │   │   └── content_hash.py # Hash-based change detection
│   │   ├── ingestion/          # Ingestion tools
│   │   │   ├── files.py
│   │   │   ├── classifier.py
│   │   │   ├── digest.py
│   │   │   ├── queue.py
│   │   │   ├── scorer.py
│   │   │   ├── token_budget.py
│   │   │   └── handlers/       # File type handlers
│   │   ├── synthesis/          # Synthesis tools (predictive identity model)
│   │   │   ├── temporal.py     # Yearly profiles, evolution, influence timeline
│   │   │   ├── private_profile.py  # Contract-compliant behavioral profile
│   │   │   ├── profile.py      # Profile access utilities
│   │   │   ├── summary.py      # Summary tools
│   │   │   └── project_patterns.py  # Behavioral patterns from projects/tasks
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
    │
    │   # Standard agent pattern: config/, logs/, prompts/, state/
    │   # - config/  : Agent configuration files
    │   # - logs/    : Agent activity logs (stdout)
    │   # - prompts/ : Prompt templates used by Python
    │   # - state/   : All data the agent reads or writes
    │
    ├── shared/                 # Cross-agent resources
    │   ├── config/             # System-wide configuration
    │   ├── logs/               # System-wide logs
    │   └── state/              # System-wide state
    │       ├── identity/       # Agent identity files
    │       │   ├── _core.identity.md
    │       │   └── [agent].identity.md
    │       ├── profile/        # Profile contract and policy
    │       │   ├── profile.contract.md
    │       │   └── redaction.policy.md
    │       ├── lifelog/        # Life log entries
    │       │   └── [yyyy]/
    │       │       └── [yyyy-mm-dd].md
    │       ├── signals/        # Inter-agent triggers
    │       ├── notifications/  # User notifications
    │       └── evolution/      # Identity evolution proposals
    │
    ├── ingestion/              # Ingestion Agent (The Archivist)
    │   ├── config/             # config.json, processed_hashes.json
    │   ├── logs/
    │   ├── prompts/            # process_file.md
    │   └── state/
    │       ├── inbox/          # pending/, processing/, processed/, failed/, deferred/
    │       ├── digests/        # {hash}.json files (LLM summaries)
    │       ├── state.json
    │       ├── queue.json
    │       └── budget.json
    │
    ├── summary/                # Summary Agent (The Historian)
    │   ├── config/
    │   ├── logs/
    │   ├── prompts/            # summarize_year.md
    │   └── state/
    │
    ├── synthesis/              # Synthesis Agent (The Keeper)
    │   ├── config/
    │   ├── logs/
    │   ├── prompts/            # temporal.md, extract_behavioral.md
    │   └── state/
    │       ├── profile/        # profile.YYYY.md, profile.current.md, evolution.md, influences_timeline.md
    │       └── processed_summaries.hash  # Hash of summaries last processed
    │
    ├── world/                  # World Agent (The Scout)
    │   ├── config/
    │   ├── logs/
    │   ├── prompts/            # discovery_sweep.md
    │   └── state/
    │       ├── opportunities/  # opportunities.json
    │       └── processed_profile.hash    # Hash of profile last processed
    │
    ├── attention/              # Attention Agent (The Curator)
    │   ├── config/
    │   ├── logs/
    │   ├── prompts/            # morning.md, evening.md, proactive.md
    │   └── state/
    │       ├── queue/          # surfacing_queue.json, energy logs
    │       └── patterns.cache.json       # Cached pattern detection results
    │
    ├── interaction/            # Interaction Agent (The Caring Friend)
    │   ├── config/
    │   ├── logs/
    │   ├── prompts/
    │   └── state/
    │       ├── conversations/  # session files
    │       └── cards/          # received cards
    │
    ├── worker/                 # Worker Agent (The Executor)
    │   ├── config/
    │   ├── logs/
    │   ├── prompts/            # process_tasks.md, execute_actions.md, execute_research.md
    │   └── state/
    │       ├── tasks/          # queue.json, daily/, results/
    │       ├── projects/       # {id}.json files
    │       │   └── notes/      # {project_id}.md files (project notes)
    │       ├── actions/        # pending/, completed/
    │       └── archive/        # archived projects with behavioral metadata
    │
    └── evolution/              # Evolution Agent (The Evolver)
        ├── config/
        ├── logs/
        ├── prompts/            # assess_health.md, analyze_system.md, check_evolution.md
        └── state/
            ├── output/         # capabilities.md
            └── processed_synthesis.hash  # Hash of synthesis last processed
```

---

## Profile Governance

Profiles are authoritative artifacts representing user identity. To prevent corruption and leakage, strict governance applies.

### Profile Types

| Type | Location | Authority | Purpose |
|------|----------|-----------|---------|
| Private | `data/synthesis/state/profile/profile.current.md` | Synthesis Agent | Internal identity model |
| Public | `data/synthesis/state/profile/profile.public.current.md` | Public Profile Generator | Safe external sharing |

### Write Authority

- **Synthesis Agent**: Sole authority for private profiles
- **Public Profile Generator**: Sole authority for public profiles (`python -m src.profile make-public`)
- **All other agents**: May read profiles and emit observation signals, but never write

### Signal-Based Contributions

Agents contribute to profile updates by emitting observations to `profile_observations.json`:

```json
{
  "agent": "interaction",
  "type": "behavioral_pattern",
  "observation": "User declined social event citing need for rest",
  "confidence": "medium",
  "suggested_update": {
    "section": "Failure Modes",
    "action": "strengthen"
  }
}
```

Synthesis reads and integrates these signals. Signals are suggestions, not commands.

### Profile Contract

All profiles must comply with `data/shared/state/profile/profile.contract.md`:
- JSON frontmatter
- Canonical section order (Identity Constraints → Failure Modes → Behavioral Attractors → Utility Tradeoffs → Epistemic Style → Narrative Identity)
- Profile item microformat with evidence pointers

See `docs/governance.md` for complete governance specification.

---

## Agents Reference

| Agent | Check Interval | Triggers | Signals Out | Hash Verification |
|-------|---------------|----------|-------------|-------------------|
| Ingestion | 30s | `inbox_changed`, pending files | `logs_updated` | Per-file digests |
| Summary | 5min | `logs_updated` | `summaries_updated` | `_summary.hash` per year |
| Synthesis | 10min | `summaries_updated` | `synthesis_updated` | `processed_summaries.hash` |
| World | 1hr | `synthesis_updated`, 24hr timer | `opportunities_updated` | `processed_profile.hash` |
| Attention | 5min | time windows, `proactive_gaps` | `attention_delivered` | `patterns.cache.json` |
| Interaction | on-demand | user messages | — | — |
| Worker | 30s | pending tasks, research tasks | `task_completed` | Task evaluation tracking |
| Evolution | 30min | `synthesis_updated`, 6hr timer | `proactive_gaps`, `agent_guidance` | `processed_synthesis.hash` |

**Hash verification prevents redundant work:** Agents verify that input data actually changed since their last run before processing, even when a signal is received. This prevents cascading unnecessary API calls when signals fire but underlying data is unchanged.

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

**Batch Processing:**

Ingestion uses batch processing to minimize API calls:

```bash
python main.py ingest                      # Default batch size (5 files)
python main.py ingest --batch-size 10      # Custom batch size
python main.py ingest ~/Documents -r       # External directory
```

Batch processing:
- Groups files by size/count for optimal API efficiency
- Requests structured JSON output instead of tool calls
- Large files become single-file batches (still efficient - no tool call overhead)

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

### Task-Based Approval Workflow

Actions requiring approval are surfaced as tasks in the "From Euno" project. Users approve or reject using familiar task interactions:

```
Action created (requires_approval=true)
    ↓
Approval task created in "From Euno" project
    ↓
User sees task with rich markdown description
    ↓
┌─────────────────────────────────────────┐
│ Complete task (checkbox) → APPROVE      │
│ Delete task              → REJECT       │
└─────────────────────────────────────────┘
    ↓
Action status updated, Worker executes if approved
```

**Approval task structure:**
```json
{
  "id": "task-xxx",
  "description": "## Approval Needed: Calendar Create\n\n**Summary here**\n\nDetails...",
  "type": "approval",
  "project_id": "project-euno",
  "action_id": "action-xxx",
  "delegation": {
    "strategy": "user_approval",
    "requires_approval": true
  }
}
```

**Key functions:**
- `create_approval_task()` — Creates rich markdown task linked to action
- `update_task_status()` — When completing, calls `approve_action()` if `action_id` present
- `delete_task()` — When deleting, calls `reject_action()` if `action_id` present

This eliminates the need for a separate approval UI—users manage approvals through the same task interface they already use.

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
  "values_alignment": ["growth"],
  "meta": {
    "total_tasks_created": 5,
    "tasks_completed": 3
  }
}
```

**Archived projects** include behavioral metadata:

```json
{
  "archived": true,
  "archived_at": "2025-12-27T10:00:00",
  "archive_metadata": {
    "outcome": "completed",
    "reason": "Reached conversational fluency",
    "completion_rate": 0.8,
    "tasks_abandoned": 1,
    "age_days": 180
  }
}
```

**Project notes** are stored in `data/worker/state/projects/notes/{project_id}.md` with newest entries prepended:

```markdown
## 2024-12-27 10:30 - Research: Language Schools
[Auto-generated by Worker Agent]

### Summary
Found 3 language schools within 30 minutes...

---

## 2024-12-25 14:00 - Note
Manual user note here...

---
```

### Task

```json
{
  "id": "task-xxx",
  "description": "Find conversation groups",
  "type": "research",
  "project_id": "project-xxx",
  "action_id": null,
  "delegation": {
    "strategy": "agent_autonomous",
    "requires_approval": false
  },
  "scheduling": {
    "due_date": "2025-12-22",
    "energy_level": "medium"
  },
  "rollover": {
    "original_date": null,
    "times_rolled": 0
  }
}
```

**Fields:**
- `action_id` — Links to a pending action (for approval tasks). When present, completing the task approves the action; deleting rejects it.

**Archived tasks** include behavioral metadata:

```json
{
  "status": "archived",
  "archived_at": "2025-12-27T10:00:00",
  "archive_metadata": {
    "outcome": "abandoned",
    "reason": "No longer relevant",
    "times_rolled": 3,
    "age_days": 14,
    "original_priority": "high",
    "was_scheduled": true
  }
}
```

**Research tasks** with `type: "research"` and `delegation.strategy: "agent_autonomous"` are auto-executed by the Worker Agent, which:
1. Executes research using web fetch tools
2. Stores results
3. Appends findings to project notes
4. Sends notification to user
5. Marks task completed

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
GET  /api/tasks/completed
POST /api/tasks
PUT  /api/tasks/{id}/status
POST /api/tasks/{id}/archive
DELETE /api/tasks/{id}

GET  /api/projects
POST /api/projects
GET  /api/projects/{id}/notes
POST /api/projects/{id}/notes
POST /api/projects/{id}/archive
POST /api/projects/{id}/complete
DELETE /api/projects/{id}

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
| `init` | `{notifications, tasks, projects, timestamp}` | Initial state on connection |
| `notification_update` | notification object | New or updated notification |
| `notification_removed` | `{id}` | Notification dismissed/deleted |
| `tasks_update` | `{tasks}` | Task queue changed (includes all statuses) |
| `projects_update` | `{projects}` | Projects changed |
| `ping` | empty | Keepalive (every 30s) |

The server watches:
- `data/shared/state/notifications/` for notification file changes
- `data/ingestion/state/inbox/` for queue status changes (synthetic notifications)
- `data/worker/state/tasks/` for task queue changes
- `data/worker/state/projects/` for project changes

**Note:** The `tasks_update` event sends all tasks (pending and completed) so the frontend can properly split and display them. The frontend filters into separate lists for display.

---

## User Interface

*See [user-experience.md](user-experience.md) for detailed UI/UX philosophy.*

### Current Design (Context-First)

The UI is context-first: it surfaces what matters before you ask. Chat is available for depth, but the primary value is delivered through time-aware contextual views.

**Principles:**

- **Ambient over interactive** — Value delivered before you interact
- **Context-appropriate** — UI morphs based on time of day, energy, what's coming
- **Anticipatory** — Surfaces what's relevant now, what you might have forgotten
- **Progressive disclosure** — Glance (2s) → Scan (10s) → Engage (unlimited)
- **Conversation is depth** — Chat for thinking through, not for commands

### Time-Aware Views

The `/api/context` endpoint auto-detects the appropriate view:

| Time | View | Purpose |
|------|------|---------|
| 7-10am | Morning | Full briefing: schedule, tasks, "on your mind", noticed patterns |
| 10am-6pm | Active | Minimal, focus-protecting: current/next activity, surfaced count |
| 6-10pm | Evening | Reflection: day summary, open threads, tomorrow preview |
| Sunday | Weekly | Patterns, time analysis, relationships, next week |

### Layout (Morning View)

```
┌─────────────────────────────────────┐
│  Good morning                       │
│                                     │
│  TODAY                              │
│  • Deep work window until 11am      │
│  • 11:30 Call with Sarah            │
│                                     │
│  ON YOUR MIND                       │
│  You've mentioned X three times...  │
│  [Let's talk]                       │
│                                     │
│  NOTICED                            │
│  Energy has been low since Tuesday  │
│                                     │
├─────────────────────────────────────┤
│  [Talk to me...]        [📎] [🔔] [✓]│
└─────────────────────────────────────┘
```

### Components

**Context View (Primary):**
- Time-aware content sections
- "On Your Mind" — recurring topics from recent logs
- "Noticed" — patterns, relationship neglect, energy observations
- Action prompts to engage deeper

**Chat Overlay:**
- Opens when clicking input or action buttons
- Full conversation capability
- "← Back to overview" returns to context view
- Preserves all existing chat functionality

**Side Panels:**
- Notifications panel (bell icon) — agent activity, proactive surfaces
- Tasks panel (list icon) — today's tasks, projects
- Slide in from right, updates via SSE
- Quick-add task input

### Visual Style

- Typography-first: black text on white
- Generous whitespace
- Minimal UI chrome
- Context sections with subtle hierarchy
- Chat as overlay, not primary surface

---

## Running

```bash
# Web server with background agents (daily use)
python main.py serve

# Interactive chat only
python main.py chat

# Batch ingestion
python main.py ingest                    # Process inbox
python main.py ingest ~/Documents -r     # Process directory recursively
python main.py ingest --batch-size 10    # Custom batch size (default: 5)

# Individual commands
python main.py morning      # Morning attention
python main.py evening      # Evening reflection
python main.py discover     # World discovery sweep
python main.py introspect   # System analysis
python main.py evolve       # Review identity proposals
```
