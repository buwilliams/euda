# Data

Rules for the major entities in the system and how they relate.

- All configs, logs, and state is stored in `data/{agents|jobs|system}/*`

## Agent

Every agent (including the user) shares the same four-category structure:
- **Identity** → `identity.md`
- **Cognition** → `prompts/` + system `metacognition` config
- **Memory** → `memory/short-term.jsonl` + `memory/long-term/`
- **Behavior** → `config.json` (tools, triggers, consolidation)

Directory structure:
- **Config:** `data/agents/{id}/config.json`
  - id, name, enabled, state, order, tools[], triggers[]
  - token_budget{}: frequency ("daily"|"hourly"|"weekly"|"monthly"), input_ratio, output_ratio
  - consolidation{}: enabled, trigger (e.g., "time:evening")
  - State: "enabled", "disabled", "paused" (paused requires manual intervention)
  - Triggers define which trigger jobs the agent receives
- **Identity:** `data/agents/{id}/identity.md`
  - Evolves over time based on long-term memory
  - For AI agents: purpose, behavioral rules, voice
  - For user: biographical info, wants/fears, stable attractors
  - Template: `identity.template.md` — preserved during Fresh Start for reinitialization
- **Memory:**
  - Short-term: `data/agents/{id}/memory/short-term.jsonl` (90-day rolling)
  - Long-term: `data/agents/{id}/memory/long-term/{yyyy}/{yyyy-mm-dd}.md` (year-based archive)
- **State:** `data/agents/{id}/state/conversation/{session-id}.md`
- **Logs:** `data/agents/{id}/logs/{date}.jsonl`

No Python code needed to create new agents — just config and identity files.

### User Agent

The user is agent `user` with the same structure as AI agents:
- Config defines tools available through the UI
- Identity contains purpose, patterns, values
- Short-term memory tracks what's on their mind (90 days)
- Long-term memory archives important events indefinitely

### Short-term Memory

- JSONL file: `data/agents/{id}/memory/short-term.jsonl`
- Tracks important items for proactive agent attention
- Fields: id, date_mentioned, date_expected, type, short_description
- Types: person, place, thing, goal, concern, idea, learning, behavior
- Entries expire after 90 days from date_mentioned
- Expired entries archive to long-term memory

### Long-term Memory

- One markdown file per day: `data/agents/{id}/memory/long-term/{yyyy}/{yyyy-mm-dd}.md`
- Chronological archive preserved before interpretation
- Consolidate phase writes to it; agents read from it for context
- Capture lived experience with high fidelity — memory, not meaning
- Content is freeform markdown with timestamps for entries

### Memory Flow

Memory moves through two phases:

- **Append phase** (automatic after conversations)
  - Lightweight extraction that adds noteworthy items to short-term memory
  - Runs automatically after each chat() call
  - No job created — invisible to user
  - Chat agent's user-relevant items cross-pollinate to user's memory (person, place, goal, concern, idea)

- **Consolidate phase** (triggered, creates visible jobs)
  - Heavy analysis triggered by `time:evening` or custom trigger
  - Creates `Trigger:consolidation:{date}` jobs that appear in agent's queue
  - Uses RLM `extract_identity()` to analyze long-term memory for identity updates
  - Discovers and validates behavioral patterns
  - Updates identity with new patterns, interests, and biographical information

### RLM (Recursive Language Model)

RLM provides intelligent access to long-term memory via iterative exploration:
- **Location:** `src/rlm/`
- **Purpose:** Semantic search and pattern analysis across large memory archives
- **Methods:**
  - `analyze(query, memory)` — Open-ended exploration of memory
  - `recall(query, memory)` — Find specific facts or events
  - `extract_identity(memory, current_identity)` — Analyze memory for identity updates
  - `process_conversation(conversation, context)` — Extract significant items from conversations

RLM is used during consolidation to evolve identity based on observed patterns in long-term memory, rather than simple rule-based analysis.

### File Import via Jobs

External files are imported to long-term memory through job-based processing:
- **Command:** `euno store <path>` creates `Store:ingest:{timestamp}` jobs
- **Deduplication:** Content hash stored as job tag (`store:hash:{sha256}`)
- **Assets:** Files attached to job as assets
- **Processing:** Chat agent processes job, extracts dates, writes to long-term memory
- **Tracking:** Job completion marks content as processed (no separate manifest)

### Identity Schema

All agents (including user) share the same identity schema stored in `identity.md`:
- Purpose (what drives them / why they exist)
- Behavioral Rules (learned must/must not constraints)
- Voice (communication style)
- Wants and Fears (what they pursue and avoid)
- Stable Attractors (patterns they return to under stress)
- Notable Events (significant consistent or surprising actions)
- Influences (people, places, experiences that shape them)
- Interests (current goals, projects, focus areas)
- Biographical Information (factual details)

AI agents start with Purpose, Behavioral Rules, Voice pre-filled. Users start empty. Both evolve through consolidation and can develop any section over time.

Historical identities: `data/agents/{id}/identity.{yyyy}.md`

### Agent Behavior

- Capabilities defined by which tools it has access to
- All agents share ethical constraints defined in the core identity
- No coercion, no manipulation, no bypassing user resistance
- Treat user resistance as information, not opposition
- Require explicit user affirmation before irreversible actions

## Job

- SQLite database: `data/jobs/db.sqlite`
- Hierarchical — any job can contain sub-jobs via parent_id
- All agents can see all jobs — visibility is universal
- Fields: id, name, parent_id, status, description, due_date, someday, tags, assignees, assignee, created_at, updated_at, completed_at, created_by
- Status: todo, working, done, error, archived
- Assets stored as files: `data/jobs/assets/{job-id}/{filename}`
- Use SQLite because indexing and querying is required

### Job Assets

Job assets are files attached to a job. They serve multiple purposes:
- **Integration data**: Uploaded files, imported content from external sources
- **Work products**: Documents, reports, analysis results created by agents
- **Context**: Supporting materials needed for job completion

All integrations (file uploads, email import, etc.) should store content as job assets rather than in separate directories. This ensures:
- Content is tied to the job that processes it
- Agents can use standard asset tools (`read_asset`, `write_asset`, `list_assets`)
- Cleanup happens naturally when jobs are archived/deleted

### Blocked Jobs

Jobs can be blocked when waiting on external input. This prevents agents from repeatedly polling the same job.

**Blocking tags:**
- `waiting:{reason}` — Waiting on external input (e.g., `waiting:logan`, `waiting:user-input`)
- `blocked:{reason}` — Blocked for other reasons

**Agent behavior:**
When an agent cannot progress on a job due to external dependencies:
1. Add a `waiting:` tag: `update_job(job_id, tags=[...existing, "waiting:logan"])`
2. Log the reason: `add_job_log(job_id, "Blocked: waiting for Logan's QA findings")`
3. Call `done_working()` to end the work cycle

**Actionable filter:**
The `list_jobs(actionable=True)` filter excludes jobs with `waiting:*` or `blocked:*` tags.

**Unblocking:**
Jobs are automatically unblocked when the user:
- Edits an asset on the job
- Sends feedback about the job
- Calls `POST /api/jobs/{id}/unblock` explicitly

Unblocking removes the blocking tags and notifies assigned agents that the job is actionable again.

## Config

- System config: `data/system/config.json`
- Contains: version, llm provider settings, logging config, agent limits, schedules
- Schedules define named times that create `Trigger:{name}:{date}` jobs
- Use flat files for configuration, not a database

## Acceptance Tests

These tests verify the memory flow works correctly. Run with dev CLI.

### Memory Extraction Test

Verifies chat conversations extract to short-term memory.

```bash
python main.py dev memory chat --json > /tmp/before.json
python main.py chat  # Say: "I'm planning to visit Tokyo for a conference"
python main.py dev memory chat --json > /tmp/after.json
```

**Pass**: New items appear in chat's short-term memory for place/idea types.

### User Memory Cross-Pollination Test

Verifies user-relevant items from chat flow to user's memory.

```bash
python main.py dev memory user --short  # Check before
python main.py chat  # Mention: "Casey suggested we visit Paris next summer"
python main.py dev memory user --short  # Check after
```

**Pass**: User's short-term memory contains person (Casey) and place (Paris) items.

### Consolidation Persistence Test

Verifies identity updates from consolidation persist.

```bash
python main.py dev identity chat > /tmp/identity-before.md
python main.py dev consolidate chat --consolidate
python main.py dev identity chat > /tmp/identity-after.md
sleep 120  # Wait 2 minutes
python main.py dev identity chat > /tmp/identity-final.md
```

**Pass**: Identity contains "Consolidation Update" section that persists (not overwritten).

### Cross-Agent Memory Search Test

Verifies agents can search other agents' memories.

```bash
python main.py dev tool search_all_memory '{"query": "some_term"}'
```

**Pass**: Returns results with `agent_id` field from multiple agents.

### Background Job Pacing Test

Verifies background-tagged jobs are paced based on load.

```bash
# Upload multiple files, then watch for pacing events
for i in 1 2 3; do curl -F "file=@test.txt" http://localhost:8000/api/upload; done
python main.py dev watch  # Look for "background_job_pacing" events
```

**Pass**: Agent logs show `background_job_pacing` events with delays scaling to utilization.
