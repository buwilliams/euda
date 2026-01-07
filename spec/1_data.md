# Data

Rules for the major entities in the system and how they relate.

- All configs, logs, and state is stored in data/{agents|jobs|system|user}/*

## Lifelog

- Chronological archive of raw human data preserved before interpretation
- One markdown file per day: `data/user/lifelog/{yyyy-mm-dd}.md`
- The Archivist writes to it; the Profiler reads from it
- Capture lived experience with high fidelity — memory, not meaning
- Content is freeform markdown with timestamps for entries

## Profile

- Derived from the lifelog, not created directly
- Data flows: Raw Data → Archivist → Lifelog → Profiler → Profile
- Current profile: `data/user/profile.current.md`
- Historical profiles: `data/user/profile.{yyyy}.md`
- Extract patterns from behavior, not stated preferences
- Profile sections:
  - Biographical information (name, contact, etc.)
  - Wants and fears (patterns that reveal desires and fears)
  - Stable attractors (patterns the person returns to)
  - Notable events and actions
  - Influences (people, places, books, experiences)
  - Interests (goals, projects, hobbies)
  - Summary of changes from previous years

## Memory

- JSONL file: `data/user/memory.jsonl`
- Tracks important items for proactive agent attention
- Fields: id, date_mentioned, date_expected, type, short_description
- Types: person, place, thing, goal, concern, idea
- Entries expire after 90 days from date_mentioned
- Included in every LLM system prompt for context

## Agent

- Config: `data/agents/{id}/config.json`
  - id, name, enabled, order, tools[], triggers[]
- Persona: `data/agents/{id}/{id}-persona.md`
- Conversation: `data/agents/{id}/state/conversation/{session-id}.md`
- Logs: `data/agents/{id}/logs/{date}.json`
- No Python code needed to create new agents — just config and persona files
- Capabilities defined by which tools it has access to
- All agents inherit from a core persona that defines shared ethical constraints
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
- Schedules define named times that emit `time:{name}` events
- Use flat files for configuration, not a database
