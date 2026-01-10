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
- Core agents are protected: chat, worker, user
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

## Design Philosophy

Profiles reflect patterns of behavior, not rigid rules:
- For users: evolves from memory through reflection (wants, fears, attractors)
- For AI agents: starts pre-filled, refines through reflection updates
- Both follow the 90/10 principle: 90% exploit known patterns, 10% explore new possibilities

See docs/3_agents.md for the cognitive foundations behind this design.

## Memory Append

- Each agent has an internal append process after conversations
- Lightweight extraction that adds noteworthy items to short-term memory
- Runs automatically when `reflection.enabled` is true
- This is automatic and invisible — no job created

## Behavioral Triggers

Agents respond to three types of behavioral triggers, each with its own prompt template:

- **Job Assignment** (`agent/job_assignment.md`): Regular job execution
  - Triggered when an agent receives a job to complete
  - Focus on executing the assigned work
  - Agent decides when work is complete
  - Jobs with `user:request` tag: write findings as asset, hand back to user

- **Exploration** (`agent/exploration.md`): Scheduled discovery
  - Configured per-agent in `config.json` under `exploration` key
  - `exploration.enabled`: Whether exploration is active (default false)
  - `exploration.trigger`: Which time trigger to use (e.g., `time:hour_04`)
  - Creates visible `Trigger:exploration:{date}` jobs
  - User-created agents can use this for autonomous discovery (see agent-lib/ for examples)
  - Apply 90/10 principle: 90% grounded in user's interests, 10% novel exposure

- **Reflection** (`agent/reflection.md`): Scheduled self-analysis
  - Triggered by consolidate trigger (e.g., `time:evening`)
  - Creates visible `Trigger:reflection:{date}` jobs
  - Agent reviews memories, identifies patterns, evolves profile
  - Uses tools: list_memory, read_long_term_memory, graduate_memory, update_own_profile

## Prompt Templates

- Base templates in `data/system/prompts/agent/`
- Agent-specific overrides in `data/agents/{agent}/prompts/`
- System checks agent-specific first, falls back to base
- Template selection based on job type:
  - `Trigger:reflection:*` jobs or `trigger:reflection` tag → reflection.md
  - `Trigger:exploration:*` jobs or `trigger:exploration` tag → exploration.md
  - Other `Trigger:*` jobs → exploration.md (legacy support)
  - All other jobs → job_assignment.md

## Job Coordination

Jobs can flow between agents and users via `handoff_job`:

- **handoff_job(job_id, to, note)**: Pass a job to another agent or user
  - Sets `pending_from` to track who handed it off
  - Enables return routing — recipient knows who to send it back to
  - Logs the handoff with optional note

**User → Agent → User (Request-Response)**
1. User asks Chat for something
2. Chat creates job with `user:request` tag, assigns to appropriate agent
3. Agent works, writes findings as asset
4. Agent calls `handoff_job(job_id, "user", "Ready for review")`
5. User reviews, provides feedback or completes

**User → Agent → User (Feedback Loop)**
1. Same as above, but user has feedback
2. User sends feedback via job context (UI routes to appropriate agent)
3. Agent revises, hands back to user
4. Loop continues until user completes

**Agent → Agent → Agent (Collaboration)**
1. Agent A is working on something
2. A needs Agent B's expertise: `handoff_job(job_id, "B", "need your input")`
3. B works, hands back: `handoff_job(job_id, "A", "here's my analysis")`
4. A continues, may involve more agents
5. Eventually returns to user or completes

**Rules:**
- Only call `complete_job` when work is truly done
- Use `handoff_job` for transfers, not `update_job`
- `pending_from` tracks return routing
- Job logs show full coordination history

## Agent Routing

- `list_agents_for_routing`: Get minimal agent info for routing decisions
  - Returns id, name, purpose (first line of profile), enabled status
  - Use when deciding which agent should handle a job

## Chat Agent Role

- Primary interface for user interaction
- Routes user requests to appropriate agents with `user:request` tag
- Can create and manage other agents
- Can answer questions about Euno by reading docs/specs
- Has access to user profile and memory for personalized responses
