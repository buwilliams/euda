# Agents

Rules for how agents work and coordinate through jobs.

## Core Principle

- Jobs are the only way agents do work — no other mechanism exists
- This creates visibility: users can see what agents are working on and what's queued

## Jobs

- A job is actionable when: assigned to an agent, status is `todo`, and due_date is NULL/today/past
- Jobs with `someday=true` are never actionable
- Jobs with future due_date are not actionable until that date
- Any user action that needs agent attention creates a job assigned to that agent

## Agents

- Agents poll for actionable jobs every 100ms (configurable via `poll_interval`)
- Job cache prevents database queries when no jobs are pending
- Cache is shared across all agent threads — when agent A assigns a job to agent B, the cache is notified immediately
- Agents work one job at a time — no polling during work cycle
- Disabled agents never process jobs
- Each agent runs in its own thread — one agent's work cannot block another
- When actionable jobs exist, the agent runs a work cycle until it calls `done_working`
- Agents can create jobs for themselves or other agents

## Triggers

- Triggers are configured per-agent in `config.json` under `triggers[]`
- Triggers create jobs, they do not wake agents directly
- Trigger job naming: `Trigger:{name}:{yyyy-mm-dd}`
- Trigger jobs have tag `trigger:{name}`
- Trigger types:
  - `system:start` — fires once at system startup
  - `time:{name}` — fires at scheduled times (morning, evening, hourly)

## Manager

- Loads agent configs from `data/agents/*/config.json`
- Starts each enabled agent in its own thread
- Maintains job cache per agent — cache is set when jobs are assigned
- Runs time scheduler that creates trigger jobs based on `schedules` in system config
- Creates startup trigger jobs for agents with `system:start`
- Detects missed `time:morning` and `time:evening` triggers at startup

## Work Cycle

- Agent receives ONE job per work cycle — prevents context overflow
- Agent works autonomously until calling `done_working` (max iterations configurable)
- After `done_working`, manager checks for more jobs and starts another cycle if needed
- Agent decides when any job is complete — including trigger jobs
- Jobs must be explicitly completed by the agent via `complete_job`

## Agent Creation & Management

- Users create agents through the Chat agent (via chat)
- Chat uses `list_available_tools` to determine appropriate tools for new agents
- Core agents are protected and cannot be deleted: chat, worker, curator
- Custom agents can be created, modified, and deleted
- All agents get base tools: list_jobs, get_job, create_job, complete_job, add_job_log, done_working
- Changes to triggers require a restart to take effect
- Agent files: `config.json` (settings) and `profile.md` (identity/instructions)

## Agent Profiles

- Profiles define the agent's purpose, voice, and approach — not rigid rules
- Write for spirit and intention, not exhaustive instructions
- The agent uses judgment to decide which tools and operations serve the user's intent
- Avoid rule-heavy profiles that try to cover every scenario
- Trust the LLM to interpret the profile's spirit and apply it to novel situations
- Don't list available tools — they're included in the system prompt from config.json
- Good profile: "I help users track what matters to them"
- Bad profile: "When user says X, do Y. When user says Z, do W..."

## Synthesis

- Each agent has an internal Synthesis process for memory and profile management
- Synthesis runs two phases:
  - **Append**: Lightweight extraction after each conversation (adds to short-term memory)
  - **Consolidate**: Heavy analysis on daily trigger (graduates memories, updates profile)
- Consolidate trigger is configurable per-agent (default: `time:evening`)
- Synthesis replaces the deprecated Profiler, Archivist, and Adaptor agents

## Chat Agent Role

- Primary interface for user interaction
- Can create and manage other agents
- Can answer questions about Euno by reading docs/specs
- Has access to user profile and memory for personalized responses
