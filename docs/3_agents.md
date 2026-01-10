# Agents

An agent is anything the capacity to act. Both people and AIs can be agents. In Euno, an agent is defined by a continuous loop that: processes work, a personality that shapes how it acts, memory that provides context, and behavioral triggers (events that prompt action).

## Concepts

- **Agent** — An autonomous worker with identity, memory, and purpose
- **Profile** — Who the agent is: purpose, behavioral rules, voice
- **Memory** — What the agent knows: short-term (90 days) and long-term (permanent)
- **Behavior** — How the agent acts: triggered by job assignment, exploration, or reflection
- **Job** — A unit of work that flows between agents and users
- **User as Agent** — You're an agent too, just with a different interface

## Profile

A profile captures who an agent is. All profiles evolve through reflection—the difference is that AI agents start pre-filled while users start empty.

### Cognitive Core (User Profile)

1. **Humans act to pursue what they desire and avoid what they fear.**
   These wants arise from biological drives and are shaped by experience (nature and nurture).

2. **Early life is dominated by exploration.**
   People try many strategies to learn what works, what fails, and what is costly.

3. **Strategies that reliably work are exploited.**
   Successful ways of meeting needs are repeated, reinforced, and become cheaper over time.

4. **Repeated exploitation forms stable internal attractors.**
   These are patterns the person tends to return to—especially under stress—because they are familiar, efficient, or safe.

5. **Identity is the pattern of these attractors over time.**
   Identity is not raw desire, values, or stories; it is how a person has learned to reliably get what they want.

6. **The self-model is a story layered on top of behavior.**
   It helps explain, justify, and stabilize strategies, but it is incomplete and sometimes inaccurate.

7. **Lasting change requires new strategies to work under real conditions.**
   Insight alone is insufficient; identity evolves when exploration produces strategies that consistently outperform old ones.

8. **Flourishing requires balance:**
   Most life is spent exploiting known, safe strategies for stability (~90%), while a smaller portion is reserved for bounded, reversible exploration (~10%) to discover new options and maintain future safety. Pressure can support growth, but only when it preserves agency, dignity, and integration.

### Profile Schema

**User Profile:**
1. Biographical Information (name, addresses, phone numbers, etc.)
2. Wants and Fears (patterns of behavior that uncover desires and fears)
3. Stable Attractors (patterns the person returns to)
4. Notable Events and Actions (either because they are consistent or surprising)
5. Influences (people, places, books, activities, entertainment, trips, experiences, etc.)
6. Interests (goals, projects, work, hobbies, entertainment)
7. Summary of changes from previous years

**AI Agent Profile:**
1. Purpose — What the agent does
2. Behavioral Rules — Must/must not constraints
3. Voice — Communication style

## Memory

Memory gives agents context to anticipate needs.

**Short-term** (90 days): What's on the agent's mind right now. Types: person, place, thing, goal, concern, idea. After 90 days, entries move to long-term memory.

**Long-term** (permanent): Chronological record of important events. Source of truth for profile evolution.

**Flow:**
```
Conversations → Short-term Memory (automatic extraction)
                        ↓
              Reflection (scheduled trigger)
                        ↓
              Long-term Memory → Profile
```

## Behavior

Agents respond to three types of triggers, each with its own prompt:

- **Job Assignment** — Work assigned by users or other agents. Execute and complete.
- **Exploration** — Scheduled discovery. Research opportunities, create suggestions for user.
- **Reflection** — Scheduled self-analysis. Review memories, evolve profile, graduate learnings.

Prompts live in `data/system/prompts/agent/`. Agents can override with their own in `data/agents/{id}/prompts/`.

## Jobs

Jobs are how all agents coordinate. Any agent—AI or user—can spawn a job. The spawning agent may complete it directly or route it to other agents. This creates a dynamic system where work flows based on who has the capacity to act.

**Structure:**
- **Hierarchy** — Jobs nest via `parent_id`. Top-level containers organize related work.
- **System Container** — Auto-created container for system-generated jobs (triggers, etc.)
- **Assignment** — Jobs have `assignees[]`. An agent only sees jobs assigned to it.
- **Status** — `todo`, `completed`, `archived`. Only `todo` jobs are actionable.

**Tags:**
- `user-request` — User asked for this; hand findings back, don't auto-complete
- `trigger:reflection` — Scheduled self-analysis job
- `trigger:*` — Other scheduled trigger jobs

**Flow:**
- Agent spawns job → works on it → completes it
- Agent spawns job → hands off to another agent → receives it back → completes
- Exploration creates suggestion → assigns to user for review
- Reflection creates insights → may spawn follow-up jobs

**Key tools:**
- `create_job(name, description, assignees)` — Spawn new work
- `handoff_job(job_id, to, note)` — Pass to another agent or user
- `complete_job(job_id)` — Mark as done
- `pending_from` tracks return routing

**Rules:**
- Only complete when work is truly done
- Use handoff for transfers between agents
- Job logs show full coordination history
