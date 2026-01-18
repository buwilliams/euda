# Data

Rules for the major entities in the system and how they relate.

- All configs, logs, and state is stored in `data/{agents|jobs|system}/*`

## Agent

Every agent (including the user) shares the same four-category structure:
- **Identity** → `identity.md`
- **Cognition** → `prompts/` + system `metacognition` config
- **Memory** → `memory/short-term.jsonl` + `memory/long-term/`
- **Behavior** → `config.json` (tools, triggers, exploration, reflection)

Directory structure:
- **Config:** `data/agents/{id}/config.json`
  - id, name, enabled, order, tools[], triggers[]
  - exploration{}: enabled, trigger (e.g., "time:hour_04")
  - reflection{}: enabled, trigger
  - Triggers define which trigger jobs the agent receives
- **Profile:** `data/agents/{id}/identity.md`
  - Evolves over time based on long-term memory
  - For AI agents: purpose, behavioral rules, voice
  - For user: biographical info, wants/fears, stable attractors
  - Template: `identity.md.example` — preserved during Fresh Start for reinitialization
- **Memory:**
  - Short-term: `data/agents/{id}/memory/short-term.jsonl` (90-day rolling)
  - Long-term: `data/agents/{id}/memory/long-term/{yyyy}/{yyyy-mm-dd}.md` (year-based archive)
- **State:** `data/agents/{id}/state/conversation/{session-id}.md`
- **Logs:** `data/agents/{id}/logs/{date}.jsonl`

No Python code needed to create new agents — just config and profile files.

### User Agent

The user is agent `user` with the same structure as AI agents:
- Config defines tools available through the UI
- Profile contains identity, patterns, values
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
- Reflection consolidate phase writes to it; agents read from it for context
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
  - Creates `Trigger:reflection:{date}` jobs that appear in agent's queue
  - Reviews short-term memory, graduates items to long-term, updates profile

### Identity Schema (Profile)

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

AI agents start with Purpose, Behavioral Rules, Voice pre-filled. Users start empty. Both evolve through reflection and can develop any section over time.

Historical profiles: `data/agents/{id}/profile.{yyyy}.md`

### Agent Behavior

- Capabilities defined by which tools it has access to
- All agents share ethical constraints defined in the core profile
- No coercion, no manipulation, no bypassing user resistance
- Treat user resistance as information, not opposition
- Require explicit user affirmation before irreversible actions

## Job

- SQLite database: `data/jobs/db.sqlite`
- Hierarchical — any job can contain sub-jobs via parent_id
- All agents can see all jobs — visibility is universal
- Fields: id, name, parent_id, status, description, due_date, someday, tags, assignees, in_progress_by, created_at, updated_at, completed_at, created_by
- Status: todo, completed, archived
- Assets stored as files: `data/jobs/assets/{job-id}/{filename}`
- Use SQLite because indexing and querying is required

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

Verifies profile updates from consolidation persist.

```bash
python main.py dev profile chat > /tmp/profile-before.md
python main.py dev reflect chat --consolidate
python main.py dev profile chat > /tmp/profile-after.md
sleep 120  # Wait 2 minutes
python main.py dev profile chat > /tmp/profile-final.md
```

**Pass**: Profile contains "Reflection Update" section that persists (not overwritten).

### Cross-Agent Memory Search Test

Verifies agents can search other agents' memories.

```bash
python main.py dev tool search_all_memory '{"query": "some_term"}'
```

**Pass**: Returns results with `agent_id` field from multiple agents.

### Exploration Memory Injection Test

Verifies exploration prompt includes user memory.

```bash
python main.py dev prompt chat explore
```

**Pass**: Prompt contains "## User Context" section with actual user memory items.
