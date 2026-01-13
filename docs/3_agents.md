# Agents

Euno is built on two core concepts: **Agents** and **Jobs**. Agents do the work; jobs are the work.

An agent is anything with the capacity to act—both people and AIs qualify. You, the user, are an agent too; you just have a different interface (the UI) than AI agents (autonomous loops). Every agent in Euno has the same fundamental components: a profile that shapes identity, memory that provides context, tools that define capabilities, and triggers that drive behavior.

Jobs are how agents coordinate. Any agent can create a job, work on it directly, or hand it off to another agent. This creates a dynamic system where work flows based on who has the capacity and capability to act.

## Agents

### Profile

A profile defines who an agent is. AI agents start with a pre-filled profile; users start empty. Both evolve through reflection.

**AI Agent Profiles** are simple and direct:
- **Purpose** — What the agent does
- **Behavioral Rules** — Must/must not constraints
- **Voice** — Communication style

**User Profiles** are richer because humans are more complex. Euno builds your profile by observing patterns over time, guided by a model of how identity actually works:

*Humans act to pursue what they desire and avoid what they fear.* Through experience, people discover strategies that reliably meet their needs. These successful strategies get repeated and reinforced until they become stable patterns—attractors the person returns to, especially under stress. Identity isn't what someone says about themselves; it's the pattern of these attractors over time.

This has practical implications for how Euno learns about you. The system watches for:
- **Wants and Fears** — Patterns of behavior that reveal underlying desires
- **Stable Attractors** — Strategies you consistently return to
- **Notable Events** — Actions that are either consistent with patterns or surprisingly different
- **Influences** — People, places, media, and experiences that shape you
- **Interests** — Goals, projects, and activities you pursue

Flourishing requires balance: most life is spent exploiting known strategies for stability (~90%), while reserving space for bounded exploration (~10%) to discover new options. Euno respects this ratio—primarily supporting what you're already doing while occasionally surfacing novel possibilities.

### Memory

Memory gives agents context to anticipate needs. Without memory, every interaction starts from zero.

**Short-term memory** (90 days) captures what's currently on an agent's mind: people, places, things, goals, concerns, ideas, learnings, and behaviors. The last two enable self-improvement—agents can record what they've learned and behavioral patterns to refine over time. Memories are extracted automatically after conversations.

**Long-term memory** (permanent) is a chronological record of important events. When short-term memories expire, significant ones graduate to long-term storage. This archive becomes the source of truth for profile evolution.

The flow is: Conversations → Short-term Memory → Reflection → Long-term Memory → Profile updates.

### Tools

Tools define what an agent can do. Each agent's config lists the tools it has access to—this is how you control capabilities and permissions.

An agent that can't see a tool can't use it. This creates natural boundaries: a research agent might have web search tools but no file system access; a personal assistant might manage jobs but not send notifications.

Tools are registered with a `@tool` decorator in `src/tools/`. To give an agent a new capability, add the tool name to its config. To restrict an agent, remove tools from its list.

### Behavior

Agents act in response to triggers. There are three types:

**Job Assignment** — Work assigned by users or other agents. The agent executes and completes the job.

**Exploration** — Scheduled discovery where agents research opportunities aligned with your interests. Configured via `exploration.trigger` in the agent's config. Creates jobs tagged `trigger:exploration`.

**Reflection** — Scheduled self-analysis where agents process memories and update profiles. Configured via `reflection.trigger`. Creates jobs tagged `trigger:reflection`.

Each trigger type has its own prompt template. System defaults live in `data/system/prompts/agent/`; individual agents can override with custom prompts in `data/agents/{id}/prompts/`.

## Jobs

Jobs are how all agents coordinate work. Any agent can spawn a job, work on it, or route it to others.

**Structure:**
- Jobs nest hierarchically via `parent_id`—top-level jobs organize related work
- Jobs have `assignees[]`—an agent only sees jobs assigned to it
- Status is `todo`, `completed`, or `archived`—only `todo` jobs are actionable

**Tags** provide context:
- `user:request` — User asked for this; hand findings back, don't auto-complete
- `trigger:exploration` — Scheduled discovery job
- `trigger:reflection` — Scheduled self-analysis job

**Flow patterns:**
- Agent creates job → works on it → completes it
- Agent creates job → hands off to another agent → receives result → completes
- Exploration creates suggestion → assigns to user for review
- Reflection generates insight → may spawn follow-up jobs

**Key tools:**
- `create_job(name, description, assignees)` — Create new work
- `handoff_job(job_id, to, note)` — Transfer to another agent
- `complete_job(job_id)` — Mark as done

The `pending_from` field tracks return routing so jobs find their way back after handoffs. Job logs preserve the full coordination history.

---

**Technical Details:** See `spec/1_agents.md` for implementation rules, `spec/2_data.md` for data schemas.
