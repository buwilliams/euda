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

- Users create agents through the Friend agent (via chat)
- Friend uses `list_available_tools` to determine appropriate tools for new agents
- Core agents are protected and cannot be deleted: friend, worker, curator, profiler, archivist, adaptor
- Custom agents can be created, modified, and deleted
- All agents get base tools: list_jobs, get_job, create_job, complete_job, add_job_log, done_working
- Changes to triggers require a restart to take effect
- Agent files: `config.json` (settings) and `{agent}-persona.md` (instructions)

## Friend Agent Role

- Primary interface for user interaction
- Can create and manage other agents
- Can answer questions about Euno by reading docs/specs
- Has access to user profile and memory for personalized responses
