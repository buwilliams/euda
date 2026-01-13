# Agents

## Our Bold Conjecture

Euno exists to test a hypothesis: that a personalized intelligence can help someone flourish—anticipating their needs, doing good work on their behalf, and supporting their path toward eudaimonia.

The bet is that this becomes possible through a **shared agent ontology**. Humans and AI agents aren't fundamentally different kinds of things. Both have profiles that expose identity discovered over time, memory that provides context, tools that define capabilities, and triggers that drive behavior. If we model them the same way, an AI agent can truly learn a person—not as a collection of preferences, but as a pattern of stable attractors that define who they are.

This architecture is the experiment. If the shared ontology holds, Euno can grow with you: learning what you want and fear, recognizing your stable patterns, adapting its behavior through the same reflection process you use. If it doesn't hold, we'll learn why humans and AI agents need different models.

Either way, we find out.

---

Euno is built on two core concepts: **Agents** and **Jobs**. Agents do the work; jobs are the work.

An agent is anything with the capacity to act—both people and AIs qualify. You, the user, are an agent too; you just have a different interface (the UI) than AI agents (autonomous loops). Every agent in Euno has the same fundamental components: a profile that exposes identity discovered over time, memory that provides context, tools that define capabilities, and triggers that drive behavior.

Jobs are how agents coordinate. Any agent can create a job, work on it directly, or hand it off to another agent. This creates a dynamic system where work flows based on who has the capacity and capability to act.

## Agents

### Profile

A profile defines who an agent is. AI agents start with a pre-filled profile; users start empty. Both use the same structure and evolve through the same reflection process.

**Profile Schema** (all agents):
- **Purpose** — What drives them / why they exist
- **Behavioral Rules** — Learned must/must not constraints
- **Voice** — Communication style
- **Wants and Fears** — What they pursue and avoid
- **Stable Attractors** — Patterns they return to under stress
- **Notable Events** — Significant consistent or surprising actions
- **Influences** — People, places, experiences that shape them
- **Interests** — Current goals, projects, focus areas
- **Biographical Information** — Factual details

AI agents typically start with Purpose, Behavioral Rules, and Voice pre-filled. Users start empty. Over time, both can develop any section through reflection.

**Why one schema?** The same model of identity applies to both humans and AI agents. Agents act to pursue what they want and avoid what they fear. Through experience, they discover strategies that work—these get repeated and become stable patterns (attractors). Identity is the pattern of these attractors over time.

This means an AI agent can develop wants (goals it pursues), fears (outcomes it avoids), and stable attractors (behaviors it returns to). A user can have behavioral rules (learned constraints) and voice (communication style). The ontology is the same; only the starting state differs.

Flourishing requires balance: most activity exploits known strategies for stability (~90%), while reserving space for bounded exploration (~10%) to discover new options. Euno respects this ratio for all agents.

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
