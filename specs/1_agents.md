# Agents

Rules for how agents work and coordinate through topics.

## Core Principle

- Topics are the only way agents do work — no other mechanism exists
- This creates visibility: users can see what agents are working on and what's queued

## Topics

- A topic is actionable when: assigned to an agent, status is `todo`, and due_date is NULL/today/past
- Topics with `someday=true` are never actionable
- Topics with future due_date are not actionable until that date
- Any user action that needs agent attention creates a topic assigned to that agent

## Agents

- Agents poll for actionable topics every 100ms (configurable via `poll_interval`)
- Topic cache prevents database queries when no topics are pending
- Cache is shared across all agent threads — when agent A assigns a topic to agent B, the cache is notified immediately
- Agents work one topic at a time — no polling during work cycle
- Disabled agents never process topics
- Each agent runs in its own thread — one agent's work cannot block another
- When actionable topics exist, the agent runs a work cycle until it calls `done_working`
- Agents can create topics for themselves or other agents

## Triggers

- Triggers are configured per-agent in `config.json` under `triggers[]`
- Triggers create topics, they do not wake agents directly

### New Trigger Format (Recommended)

Triggers are objects that specify a topic to create on a schedule:

```json
{
  "triggers": [
    {
      "topic_name": "euno:consolidate",
      "topic_description": "Review memories, evolve identity, graduate learnings",
      "schedule": "evening"
    },
    {
      "topic_name": "euno:quote",
      "topic_description": "Generate personalized daily quote",
      "schedule": "morning"
    }
  ]
}
```

- `topic_name`: The name of the topic to create (e.g., `euno:consolidate`, `euno:quote`)
- `topic_description`: Description for the created topic (optional)
- `schedule`: Schedule name from system config (e.g., `morning`, `evening`)

### Internal Topics (`euno:*`)

Topics with names starting with `euno:` are internal system topics that execute tools directly without LLM involvement:

| Topic Name | Tool | Purpose |
|----------|------|---------|
| `euno:consolidate` | `euno_consolidate` | Run consolidation (memory analysis, identity updates) |
| `euno:quote` | `euno_quote` | Generate personalized daily quote |

These topics:
- Bypass the LLM chat loop entirely (efficient, single tool call)
- Are prevented from duplicating (only one pending per agent at a time)
- Complete automatically after tool execution

## Manager

- Loads agent configs from `data/agents/*/config.json`
- Starts each enabled agent in its own thread
- Maintains topic cache per agent — cache is set when topics are assigned
- Runs time scheduler that creates trigger topics based on `schedules` in system config
- Detects missed `time:morning` and `time:evening` triggers at startup

## Work Cycle

- Agent receives ONE topic per work cycle — prevents context overflow
- Work cycle phases: claim → plan → execute → complete
- Planning creates a brief approach (tool sequence, delegation, strategy) before execution
- Agent works autonomously until calling `done_working` (max iterations configurable)
- After `done_working`, manager checks for more topics and starts another cycle if needed
- Agent decides when any topic is complete — including trigger topics
- Topics must be explicitly completed by the agent via `complete_topic`

## Agent Creation & Management

- Users create agents through the Chat agent (via chat)
- Chat uses `list_available_tools` to determine appropriate tools for new agents
- Core agents are protected: chat, worker, user
- All agents get base tools: list_topics, get_topic, create_topic, complete_topic, add_topic_log, done_working
- Changes to triggers require a restart to take effect
- Agent files: `config.json` (settings) and `identity.md` (identity/instructions)

## Writing Agent Identities

- Identities define the agent's purpose, voice, and approach — not rigid rules
- Write for spirit and intention, not exhaustive instructions
- The agent uses judgment to decide which tools and operations serve the user's intent
- Avoid rule-heavy identities that try to cover every scenario
- Trust the LLM to interpret the identity's spirit and apply it to novel situations
- Don't list available tools — they're included in the system prompt from config.json
- Good identity: "I help users track what matters to them"
- Bad identity: "When user says X, do Y. When user says Z, do W..."

## Design Philosophy

All agents (users and AI) share the same identity schema and evolve through the same consolidation process. The only difference is starting state: AI agents start pre-filled, users start empty.

Identities reflect patterns of behavior, not rigid rules:
- Identity is the pattern of stable attractors over time
- Both users and AI agents can develop any identity section through consolidation

See docs/3_system.md for the cognitive foundations behind this design.

## Memory Append

- Each agent has an internal append process after conversations
- Lightweight extraction that adds noteworthy items to short-term memory
- Runs automatically when `consolidation.enabled` is true
- This is automatic and invisible — no topic created

## Behavioral Triggers

Agents respond to different types of topics:

- **Topic Assignment** (`agent/topic_assignment.md`): Regular topic execution
  - Triggered when an agent receives a topic to complete
  - Focus on executing the assigned work
  - Agent decides when work is complete
  - Topics with `user:request` tag: write findings as asset, hand back to user

- **Internal Topics** (`euno:*`): Direct tool execution
  - Bypass the LLM chat loop entirely for efficiency
  - Execute their mapped tool directly and complete
  - Examples:
    - `euno:consolidate` → `euno_consolidate` tool (identity analysis)
    - `euno:quote` → `euno_quote` tool (quote generation)

## Prompt Templates

- Base templates in `data/system/prompts/agent/`
- Agent-specific overrides in `data/agents/{agent}/prompts/`
- System checks agent-specific first, falls back to base
- Template selection based on topic type:
  - `euno:*` topics → bypassed (direct tool execution)
  - All other topics → topic_assignment.md

## Topic Coordination

Topics can flow between agents and users via `handoff_topic`:

- **handoff_topic(topic_id, to, note)**: Pass a topic to another agent or user
  - Sets `pending_from` to track who handed it off
  - Enables return routing — recipient knows who to send it back to
  - Logs the handoff with optional note

**User → Agent → User (Request-Response)**
1. User asks Chat for something
2. Chat creates topic with `user:request` tag, assigns to appropriate agent
3. Agent works, writes findings as asset
4. Agent calls `handoff_topic(topic_id, "user", "Ready for review")`
5. User reviews, provides feedback or completes

**User → Agent → User (Feedback Loop)**
1. Same as above, but user has feedback
2. User sends feedback via topic context (UI routes to appropriate agent)
3. Agent revises, hands back to user
4. Loop continues until user completes

**Agent → Agent → Agent (Collaboration)**
1. Agent A is working on something
2. A needs Agent B's expertise: `handoff_topic(topic_id, "B", "need your input")`
3. B works, hands back: `handoff_topic(topic_id, "A", "here's my analysis")`
4. A continues, may involve more agents
5. Eventually returns to user or completes

**Rules:**
- Only call `complete_topic` when work is truly done
- Use `handoff_topic` for transfers, not `update_topic`
- `pending_from` tracks return routing
- Topic logs show full coordination history

## Agent Routing

- `list_agents_for_routing`: Get minimal agent info for routing decisions
  - Returns id, name, purpose (first line of identity), enabled status
  - Use when deciding which agent should handle a topic

## Chat Agent Role

- Primary interface for user interaction
- Routes user requests to appropriate agents with `user:request` tag
- Can create and manage other agents
- Can answer questions about Euno by reading docs/specs
- Has access to user identity and memory for personalized responses

## Agent Ontology

Every agent shares the same four-category structure:

```
Agent = Identity + Cognition + Memory + Behavior
```

| Category | Question | What It Contains |
|----------|----------|------------------|
| **Identity** | Who am I? | Purpose, values, voice, attractors, context |
| **Cognition** | How do I think? | Reasoning (topic planning, prompts) + Metacognition (self-regulation, consolidation) |
| **Memory** | What do I know? | Short-term (90 days) + Long-term (permanent) |
| **Behavior** | What can I do? | Tools + Triggers + Modes |

### Identity

- Stored in `identity.md` as markdown sections
- Contains: Purpose, Behavioral Rules, Voice, Wants/Fears, Stable Attractors, Notable Events, Influences, Interests, Biographical Info
- Evolves through consolidation—discovered, not configured
- AI agents start pre-filled; users start empty
- Historical snapshots: `identity.{yyyy}.md`

### Memory

- **Short-term**: `memory/short-term.jsonl` — Rolling 90-day window of noteworthy items
- **Long-term**: `memory/long-term/{yyyy}/{yyyy-mm-dd}.md` — Permanent chronological archive
- Types: person, place, thing, goal, concern, idea, learning, behavior
- Flow: Conversations → Append phase → Short-term → Consolidate phase → Long-term
- Cross-pollination: Chat agent's user-relevant items flow to user's memory
- See `specs/2_data.md` for detailed memory schemas and flow

### Cognition

Cognition has two aspects:

**Reasoning** — First-order thinking (about the world)
- Topic planning: when work begins, agent creates a brief plan (tool sequence, delegation, approach)
- Defined by system prompts in `data/system/prompts/agent/`
- Agent-specific overrides in `data/agents/{id}/prompts/`
- Template selection based on topic type (topic_assignment, consolidation)

**Metacognition** — Second-order thinking (about thinking)
- Self-awareness, self-regulation, and self-improvement
- Inherent to all agents, not optional
- Configuration in `data/system/config.json` under `metacognition`

## Metacognition (Cognition Subsystem)

Metacognition is the self-regulation and self-improvement component of Cognition:
- **Self-regulation** — Token awareness, progress detection (keeping the agent healthy)
- **Self-improvement** — Consolidation (helping the agent grow)

### Agent States

Agents have three possible states:

| State | Description | Can Run? | Set By |
|-------|-------------|----------|--------|
| `enabled` | Normal operation | Yes | User/CLI/API |
| `disabled` | User explicitly disabled | No | User/CLI/API |
| `paused` | Threshold breach - awaiting manual intervention | No | System (auto) |

**Transition Rules:**
- `enabled` → `paused`: System auto-pauses when token threshold exceeded
- `paused` → `enabled`: Manual intervention via CLI/UI/API required
- Any state → `disabled`: User explicitly disables

### Token Awareness

Unified token tracking and budget enforcement:

- **Real agent_id required**: All LLM calls must use a real agent_id defined in `data/agents/*/config.json`
  - Never use made-up agent_ids like "system", "transcribe", "tts", etc.
  - Sub-agent patterns are allowed: `{agent_id}/planning`, `{agent_id}/reflection`
  - This ensures all token usage is tracked against real agent budgets
- **Pre-call estimation**: Estimates input tokens using tiktoken before API calls
- **Post-call recording**: Records actual input/output tokens after API calls
- **Per-agent budgets**: Global budget split equally among enabled agents
- **Frequency-based limits**: Each agent chooses a frequency (daily, hourly, weekly, monthly)
- **Separate I/O thresholds**: Default 80% input, 20% output token allocation
- **Auto-pause**: Agents exceeding thresholds are paused (requires manual resume)
- **Incident tracking**: Threshold breaches logged as incidents

Budget calculation:
```
per_agent_monthly = global_budget_tokens / enabled_agent_count
per_agent_daily = per_agent_monthly / 31
per_agent_hourly = per_agent_daily / 24
```

Configuration in agent `config.json`:
```json
{
  "token_budget": {
    "frequency": "daily",
    "input_ratio": 0.8,
    "output_ratio": 0.2
  }
}
```

### Progress Awareness

- Counts tool calls per iteration (max_tool_calls_per_iteration)
- Detects stuck patterns: same tool called repeatedly with identical inputs
- Breaks work cycle when stuck detected
- Configuration in `metacognition.progress`

### Consolidation (Self-Improvement)

Consolidation is the metacognitive process of self-analysis and growth:

- **Append phase** (automatic after conversations)
  - Lightweight extraction of noteworthy items to short-term memory
  - Runs automatically after each chat() call
  - No topic created — invisible to user

- **Consolidate phase** (triggered, creates visible topics)
  - Triggered by `euno:consolidate` trigger in agent config
  - Creates `euno:consolidate` topic that executes directly (no LLM loop)
  - Reviews long-term memory via RLM, updates identity
  - Implemented as `euno_consolidate` tool in `src/tools/system/consolidation/`

Consolidation is scheduled via the trigger system (see Triggers section):
```json
{
  "triggers": [
    {
      "topic_name": "euno:consolidate",
      "schedule": "evening"
    }
  ]
}
```

### Incidents

When agents breach thresholds, incidents are recorded:
- `token_threshold_exceeded`: Agent exceeded input or output token budget
- Incidents appear in logs and via `GET /api/system/incidents`
- Acknowledge incidents via `POST /api/system/incidents/{id}/acknowledge`

### Configuration

System-wide defaults in `data/system/config.json`:
```json
{
  "metacognition": {
    "token_awareness": {
      "enabled": true,
      "thresholds": {
        "warning_percent": 80,
        "pause_percent": 100
      }
    },
    "progress": { "max_tool_calls_per_iteration": 50 },
    "planning": { "enabled": true, "excluded_for": [] },
    "efficiency": { "defer_consolidation_in_work_cycles": true },
    "consolidation": {
      "append_max_tokens": 500,
      "append_batch_max_tokens": 1000,
      "consolidate_max_tokens": 2000,
      "upload_analysis_max_tokens": 1000
    }
  }
}
```

Individual agents can override specific settings in their `config.json` but rarely need to.

## Behavior

Behavior defines what agents can do and when they activate.

### Tools

- Capabilities defined by `tools[]` in agent's config.json
- All agents get base tools: list_topics, get_topic, create_topic, complete_topic, add_topic_log, done_working
- Additional tools granted per-agent based on role
- An agent cannot use tools not in its config

### Triggers

See the main Triggers section above for full documentation.

- Triggers are configured per-agent in `config.json` under `triggers[]`
- Triggers create topics, they do not wake agents directly
- New format: objects with `topic_name`, `topic_description`, `schedule`
- Legacy format: strings like `"time:morning"`, `"system:start"`

### Triggers vs Processes

Behavior defines *when* things activate via triggers. The processes themselves may belong to other categories:

| Trigger Topic Name | Activates | Process Lives In |
|------------------|-----------|------------------|
| Regular topic | Topic assignment | Behavior (tool execution via LLM) |
| `euno:consolidate` | Self-improvement | Cognition (metacognition via tool) |
| `euno:quote` | Quote generation | System (direct tool execution) |

## Observation System

The observation system enables agents to notice relevant content across different sources and surface observations proactively.

### Overview

- Agents can declare interests via memory entries of type `interest`
- Watchers monitor content sources (chat, calendar, mastodon)
- When content matches an agent's interests, an observation topic is created
- Agent reviews observation and may surface it in chat

### Interest Sources

Interests come from two places:

1. **Memory entries** with `type: "interest"` — keywords/themes the agent is tracking
2. **Active topics** assigned to the agent — titles and descriptions expand the interest surface

```json
// Example interest memory entry
{
  "id": "mem-abc12345",
  "type": "interest",
  "short_description": "decentralized identity",
  "date_mentioned": "2026-01-25"
}
```

Interests expire after 90 days if not reinforced (standard memory expiration).

### Content Sources

| Source | Monitoring | Matching |
|--------|------------|----------|
| **Chat** | Real-time (inline) | Every message checked against interests |
| **Calendar** | Periodic (watcher) | New/changed events checked |
| **Mastodon** | Periodic (watcher) | User's posts checked |

Chat is real-time to make Euno feel responsive. Calendar and Mastodon are periodic since they change less frequently.

### Watchers

Watchers are background processes in the manager that:

1. Poll content sources periodically (every 15-30 min for calendar/mastodon)
2. Track last-seen state to detect changes
3. Check new content against agent interests (keyword matching, no LLM)
4. Create observation topics when matches found

Chat matching is different — it hooks into chat processing inline rather than polling.

### Matching Logic

Matching is lightweight (no LLM):

```python
def matches_interests(content: str, agent_id: str) -> bool:
    # Load interest-type memories for agent
    interests = [m for m in list_memory(agent_id) if m["type"] == "interest"]
    keywords = [m["short_description"].lower() for m in interests]

    # Also check active topics
    active_topics = list_topics(assignee=agent_id, status=["todo", "working"])
    for topic in active_topics:
        keywords.extend(extract_keywords(topic["name"]))

    # Simple keyword matching
    content_lower = content.lower()
    return any(kw in content_lower for kw in keywords)
```

### Observation Topics

When a match is found:

1. Create topic assigned to the agent with tag `observation`
2. Topic name: `observation:{source}:{timestamp}`
3. Topic description includes: matched content, source, matched keyword
4. Agent works the observation during its normal cycle
5. Agent decides whether to surface to user or dismiss

### Agent Configuration

Agents opt into observations via config:

```json
{
  "observation": {
    "enabled": true,
    "sources": ["chat", "calendar", "mastodon"],
    "cooldown_minutes": 30,
    "max_per_day": 5
  }
}
```

- `enabled`: Whether to monitor for this agent
- `sources`: Which sources to monitor
- `cooldown_minutes`: Minimum time between observations from same source
- `max_per_day`: Cap on daily observations (prevents spam)

### Interest Population

Interests are populated through use, not pre-seeded:

1. **Topic assignment**: When user assigns a topic to an observing agent, system extracts keywords and creates interest memories
2. **Consolidation**: Agent during consolidation can add/remove interests based on patterns
3. **Manual**: User can add interest memories directly

### Chat Integration

For chat, interest checking hooks into the message flow:

1. User sends message to Chat agent
2. Before/after processing, check message against all observing agents' interests
3. If match found, queue observation (don't interrupt current chat)
4. Observation surfaced when user next interacts or agent works its queue

### Implementation Notes

- Watchers run in manager, one thread per source type
- Interest cache rebuilds periodically or on memory file change
- No LLM calls during matching — all keyword/pattern based
- Observation topics are low-priority (don't preempt regular work)
