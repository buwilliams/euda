# Data

Rules for the major entities in the system and how they relate.

- All configs, logs, and state is stored in `data/{agents|topics|system}/*`

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
  - Triggers define which trigger topics the agent receives
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
  - No topic created — invisible to user
  - Chat agent's user-relevant items cross-pollinate to user's memory (person, place, goal, concern, idea)

- **Consolidate phase** (triggered, creates visible topics)
  - Heavy analysis triggered by `euno:consolidate` topic (scheduled via object triggers)
  - Creates `euno:consolidate` topic that appears in agent's queue
  - Uses RLM `extract_identity()` to analyze long-term memory for identity updates
  - Discovers and validates behavioral patterns
  - Updates identity with new patterns, interests, and biographical information

### RLM (Recursive Language Model)

RLM provides intelligent access to long-term memory via iterative exploration:
- **Location:** `src/agent/rlm/`
- **Purpose:** Semantic search and pattern analysis across large memory archives
- **Methods:**
  - `analyze(query, memory)` — Open-ended exploration of memory
  - `recall(query, memory)` — Find specific facts or events
  - `extract_identity(memory, current_identity)` — Analyze memory for identity updates
  - `process_conversation(conversation, context)` — Extract significant items from conversations

RLM is used during consolidation to evolve identity based on observed patterns in long-term memory, rather than simple rule-based analysis.

### File Import via Topics

External files are imported to long-term memory through topic-based processing:
- **Command:** `euno store <path>` creates `Store:ingest:{timestamp}` topics
- **Deduplication:** Content hash stored as topic tag (`store:hash:{sha256}`)
- **Assets:** Files attached to topic as assets
- **Processing:** Chat agent processes topic, extracts dates, writes to long-term memory
- **Tracking:** Topic completion marks content as processed (no separate manifest)

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

### Historical Identity Snapshots

At year boundaries, consolidation creates historical snapshots of agent identities:
- **Location:** `data/agents/{id}/identity.{yyyy}.md`
- **Timing:** Created in the first week of January for the previous year
- **Condition:** Only if the snapshot doesn't already exist
- **Content:** Copy of the current identity at the moment of snapshot

This preserves how an agent's identity has evolved over time, enabling:
- Longitudinal analysis of personal growth
- Recovery of previous identity states if needed
- Understanding of how patterns and values have shifted

### Agent Behavior

- Capabilities defined by which tools it has access to
- All agents share ethical constraints defined in the core identity
- No coercion, no manipulation, no bypassing user resistance
- Treat user resistance as information, not opposition
- Require explicit user affirmation before irreversible actions

## Topic

- SQLite database: `data/topics/db.sqlite`
- Hierarchical — any topic can contain sub-topics via parent_id
- All agents can see all topics — visibility is universal
- Fields: id, name, parent_id, status, description, due_date, someday, tags, assignee, created_at, updated_at, completed_at, created_by
- Status: todo, working, done, error, archived
- Assets stored as files: `data/topics/assets/{topic-id}/{filename}`
- Use SQLite because indexing and querying is required

### Topic Assets

Topic assets are files attached to a topic. They serve multiple purposes:
- **Integration data**: Uploaded files, imported content from external sources
- **Work products**: Documents, reports, analysis results created by agents
- **Context**: Supporting materials needed for topic completion

All integrations (file uploads, email import, etc.) should store content as topic assets rather than in separate directories. This ensures:
- Content is tied to the topic that processes it
- Agents can use standard asset tools (`read_asset`, `write_asset`, `list_assets`)
- Cleanup happens naturally when topics are archived/deleted

### Blocked Topics

Topics can be blocked when waiting on external input. This prevents agents from repeatedly polling the same topic.

**Blocking tags:**
- `waiting:{reason}` — Waiting on external input (e.g., `waiting:logan`, `waiting:user-input`)
- `blocked:{reason}` — Blocked for other reasons

**Agent behavior:**
When an agent cannot progress on a topic due to external dependencies:
1. Add a `waiting:` tag: `update_topic(topic_id, tags=[...existing, "waiting:logan"])`
2. Log the reason: `add_topic_log(topic_id, "Blocked: waiting for Logan's QA findings")`
3. Call `done_working()` to end the work cycle

**Actionable filter:**
The `list_topics(actionable=True)` filter excludes topics with `waiting:*` or `blocked:*` tags.

**Unblocking:**
Topics are automatically unblocked when the user:
- Edits an asset on the topic
- Sends feedback about the topic
- Calls `POST /api/topics/{id}/unblock` explicitly

Unblocking removes the blocking tags and notifies assigned agents that the topic is actionable again.

## Config

- System config: `data/system/config.json`
- Contains: version, llm provider settings, logging config, agent limits, schedules
- Schedules define named times that create topics (via object triggers in agent configs)
- Use flat files for configuration, not a database

## Acceptance Tests

These tests verify the memory flow works correctly. Run with dev CLI.

### Memory Extraction Test

Verifies chat conversations extract to short-term memory.

```bash
uv run euno dev memory chat --json > /tmp/before.json
uv run euno chat  # Say: "I'm planning to visit Tokyo for a conference"
uv run euno dev memory chat --json > /tmp/after.json
```

**Pass**: New items appear in chat's short-term memory for place/idea types.

### User Memory Cross-Pollination Test

Verifies user-relevant items from chat flow to user's memory.

```bash
uv run euno dev memory user --short  # Check before
uv run euno chat  # Mention: "Casey suggested we visit Paris next summer"
uv run euno dev memory user --short  # Check after
```

**Pass**: User's short-term memory contains person (Casey) and place (Paris) items.

### Consolidation Persistence Test

Verifies identity updates from consolidation persist.

```bash
uv run euno dev identity chat > /tmp/identity-before.md
uv run euno dev consolidate chat --consolidate
uv run euno dev identity chat > /tmp/identity-after.md
sleep 120  # Wait 2 minutes
uv run euno dev identity chat > /tmp/identity-final.md
```

**Pass**: Identity contains "Consolidation Update" section that persists (not overwritten).

### Cross-Agent Memory Search Test

Verifies agents can search other agents' memories.

```bash
uv run euno dev tool search_all_memory '{"query": "some_term"}'
```

**Pass**: Returns results with `agent_id` field from multiple agents.

### Background Topic Pacing Test

Verifies work cycles are paced to prevent runaway spinning.

```bash
# Upload multiple files, observe agent doesn't spin continuously
for i in 1 2 3; do curl -F "file=@test.txt" http://localhost:8000/api/upload; done
uv run euno dev watch  # Observe work_cycle events with natural delays
```

**Pass**: Work cycles have minimum 500ms delay between them, preventing CPU spinning.
