# Data

Rules for the major entities in the system and how they relate.

- All configs, logs, and state is stored in `data/{agents|jobs|system}/*`

## Agent

Every agent (including the user) shares the same structure:

- **Config:** `data/agents/{id}/config.json`
  - id, name, enabled, order, tools[], triggers[]
  - exploration{}: enabled, trigger (e.g., "time:hour_04")
  - reflection{}: enabled, trigger
  - Triggers define which trigger jobs the agent receives
- **Profile:** `data/agents/{id}/profile.md`
  - Evolves over time based on long-term memory
  - For AI agents: purpose, behavioral rules, voice
  - For user: biographical info, wants/fears, stable attractors
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

- **Consolidate phase** (triggered, creates visible jobs)
  - Heavy analysis triggered by `time:evening` or custom trigger
  - Creates `Trigger:reflection:{date}` jobs that appear in agent's queue
  - Reviews short-term memory, graduates items to long-term, updates profile

### Profile Schema

Current profile evolves based on observed behavior in long-term memory:
- Biographical information (name, contact, etc.)
- Wants and fears (patterns that reveal desires and fears)
- Stable attractors (patterns the person returns to)
- Notable events and actions
- Influences (people, places, books, experiences)
- Interests (goals, projects, hobbies)
- Summary of changes from previous years

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
