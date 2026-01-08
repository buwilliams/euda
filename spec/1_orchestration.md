# Orchestration

Rules for how Agents, Jobs, Triggers, and the Manager work together.

## Core Principle

- Jobs are the only way agents do work — no other mechanism exists
- This creates visibility: users can see what agents are working on and what's queued

## Jobs

- A job is actionable when: assigned to an agent, status is `todo`, and due_date is NULL/today/past
- Jobs with `someday=true` are never actionable
- Jobs with future due_date are not actionable until that date
- Any user action that needs agent attention creates a job assigned to that agent

## Agents

- Agents poll for actionable jobs assigned to them (default: every 30 seconds)
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
  - `lifelog:new` — fires when a lifelog entry is written

## Manager

- Loads agent configs from `data/agents/*/config.json`
- Starts each enabled agent in its own thread
- Runs time scheduler that creates trigger jobs based on `schedules` in system config
- Creates startup trigger jobs for agents with `system:start`
- Detects missed `time:morning` and `time:evening` triggers at startup

## Work Cycle

- Agent fetches all actionable jobs assigned to it
- Agent works autonomously until calling `done_working` (max iterations configurable)
- Agent decides when any job is complete — including trigger jobs
- Jobs must be explicitly completed by the agent via `complete_job`
