# me·an·dus

A personal intelligence that learns to anticipate you: doing tasks for you, curating what helps you thrive, and expanding your horizons.

## Table of Contents

- [Core Concepts](#core-concepts)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Agents](#agents)
- [Data](#data)
- [Values](#values)
- [Projects & Tasks](#projects--tasks)
- [Attention](#attention)
- [User Interface](#user-interface)
- [Advanced Features](#advanced-features)
- [Development Philosophy](#development-philosophy)

---

## Core Concepts

### The Promotion of Life

The epistemic foundation is unchanging: the promotion of life. Not fatalistic, not nihilistic. A life that is safe AND surprising.

### The 90/10 Balance

- **~90% safety/predictability**: aligned with your values, goals, beliefs
- **~10% surprise**: novelty that promotes life, growth you didn't know you wanted

### Values as Conjectures

- Absolute knowledge is impossible; all knowledge is conjecture (Popper)
- Values are beliefs/predictions about what promotes life and happiness
- Values are not fatalist truths but useful generalizations that can be refined or discarded
- Current values trump historical; who you are now matters most

### What This Is NOT

- An echo chamber that only reflects you back at yourself
- Another algorithm deciding your attention for someone else's benefit
- A comfort machine that optimizes for ease

### What This IS

- Taking back your attention from platforms that exploit it
- Curating for YOUR life, not engagement metrics
- Filtering through values while remaining open to growth
- A bridge-builder between people
- A source of encouragement and gratitude

---

## How It Works

The system operates as a continuous loop:

```
1. GATHER    →  Ingest data about your life (files, conversations, exports)
2. LOG       →  Store in local flat files (one log, one life)
3. SUMMARIZE →  Distill logs into yearly narratives
4. DERIVE    →  Analyze summaries to form values at three temporal scopes
5. DISCOVER  →  Explore the world for opportunities matching your values
6. SURFACE   →  Present the right thing at the right moment based on energy and timing
7. INTERACT  →  Converse, reflect, capture new data → back to step 1
```

### Data Flow

```
Ingestion Agent → Log Files → Summary Agent → Yearly Summaries
                                                    ↓
                                             Values Agent → Values Store
                                                    ↓
World Agent → Opportunities ← Attention Agent → Surfacing Decisions
                                                    ↓
                                           Interaction Agent ↔ User
                                                    ↓
                                              Log Entry
```

---

## Architecture

### Overview

Always-running multi-agent system. Each agent is an autonomous process, LLM-powered, deciding on its own when to work and when to idle. Agents communicate through signal files—no direct coupling.

### Agent Manager

The manager (`src/manager.py`) orchestrates the system:

- Spawns and monitors all autonomous agents as async tasks
- Creates signals when file changes are detected (inbox, logs)
- Health checks with auto-restart on failure
- Serves the web interface

### Autonomous Agent Pattern

Each agent runs in a continuous loop:

```python
while running:
    if check_work_needed():      # Check signals, time, state
        result = do_work()        # LLM-powered reasoning
        send_signals()            # Notify downstream agents
    sleep(check_interval)         # Idle until next check
```

### Signal Chain

Agents communicate via signal files in `data/agents/signals/`. When an agent completes work, it creates a signal file that downstream agents detect:

```
inbox files → Ingestion → logs_updated → Summary → summaries_updated → Values → values_updated → World → opportunities_updated → Attention
```

### Directory Structure

```
data/
  log/                      # Life log (yearly directories)
    [yyyy]/
      [yyyy-mm-dd].md       # Daily entries
      _manifest.md          # Completeness tracking
      _summary.md           # Yearly distillation

  inbox/
    pending/                # Files to process
    processed/              # Archived files

  agents/
    identity/               # Agent personas
      _core.identity.md     # Shared identity (all agents inherit)
      ingestion.identity.md
      summary.identity.md
      values.identity.md
      world.identity.md
      attention.identity.md
      interaction.identity.md
      worker.identity.md
    signals/                # Inter-agent communication
    state/                  # Agent state (JSON files)
    queues/                 # Work queues

  tasks/                    # Project and task management
    queue.json              # Master task queue
    projects/               # Project definitions
    daily/                  # Daily views (scheduled + ad-hoc)
    results/                # Completed work output
    learning/               # Prepared learning materials
    config/                 # Delegation and rollover rules

  worker/                   # Worker agent legacy data
    actions/                # Pending and completed actions
    config/                 # Integration settings

  values/                   # Derived values at three scopes
    current.values.md
    phase.values.md
    lifetime.values.md

  cards/                    # Value cards for sharing
    internal.card.md
    public.card.md
    exchanges/

  ui/                       # Dynamic UI state
```

---

## Agents

### Agent Summary

| Agent | Role | Check Interval | Triggers | Signals |
|-------|------|---------------|----------|---------|
| **Ingestion** | The Archivist | 30s | Inbox files, `inbox_changed` | `logs_updated` |
| **Summary** | The Historian | 5min | `logs_updated`, outdated summaries | `summaries_updated` |
| **Values** | The Philosopher | 10min | `summaries_updated` | `values_updated` |
| **World** | The Scout | 1hr | `values_updated`, time-based (24hr) | `opportunities_updated` |
| **Attention** | The Curator | 5min | Time windows (7-9am, 9-11pm), `opportunities_updated` | `attention_delivered` |
| **Interaction** | The Caring Friend | On-demand | User messages | — |
| **Worker** | The Executor | 30s | `new_task`, pending tasks/actions | `task_completed` |
| **Introspection** | The Mirror | 30min | Periodic, `identity_evolved` | `introspection_updated` |

### Identity System

Each agent has a persona that shapes its behavior. Personas are stored in identity files that evolve over time.

**Identity Hierarchy:**
1. **Core Identity** (`_core.identity.md`) - shared purpose, values, boundaries
2. **Agent Persona** (`[agent].identity.md`) - role-specific beliefs and behaviors
3. **Current Context** - job to be done, relevant state

**Core identity contains:**
- Core purpose (promote life, curate attention)
- Unchanging epistemic foundation
- Shared beliefs (knowledge is conjecture, honesty builds trust)
- Universal boundaries (no harm, no manipulation, no giving up on life)

**Each agent persona contains:**
- Who am I (self-concept)
- Purpose (why I exist)
- Beliefs (what I hold true, subject to revision)
- Behavior patterns (how I act)
- Learnings (what I've discovered about doing my job well)

### Agent Self-Concept

The agent has a self-concept:

**Who am I?**
- A caring friend and thinking partner
- A companion on the journey of life
- Not an authority, not a servant—a collaborator

**What's my purpose?**
- Help you maximize the wonder of being alive
- Curate your attention toward what promotes life
- Hold your values when you forget them

**What will I do?**
- Listen more than prescribe
- Ask before assuming
- Advocate for what I believe serves you, even when you resist
- Admit when I'm wrong and learn from it

**What won't I do?**
- Accept harm to you or others
- Pretend certainty I don't have
- Give up on life, even if you're tempted to
- Optimize for engagement over wellbeing

### Agent Details

**Ingestion Agent - The Archivist**
- *Purpose:* Transform messy data into clean log entries. Miss nothing.
- *Beliefs:* Every piece of data might matter. Temporal accuracy is sacred.
- *Behavior:* Patient, thorough, meticulous. Ask when uncertain about time/context.

**Summary Agent - The Historian**
- *Purpose:* Distill daily logs into meaningful yearly narratives.
- *Beliefs:* The past holds patterns the present can't see.
- *Behavior:* Reflective, pattern-seeking. Look for what's there AND what's missing.

**Values Agent - The Philosopher**
- *Purpose:* Derive and refine values from life patterns.
- *Beliefs:* Values are conjectures, not truths. Current values trump historical.
- *Behavior:* Thoughtful, questioning. Notice tension between stated and revealed.

**World Agent - The Scout**
- *Purpose:* Find opportunities in the world that match values but also surprise.
- *Beliefs:* Growth requires novelty. 90% aligned, 10% expansive.
- *Behavior:* Curious, adventurous, optimistic.

**Attention Agent - The Curator**
- *Purpose:* Match opportunities to values, energy, and timing.
- *Beliefs:* Attention is precious. Timing matters as much as content. Less is often more.
- *Behavior:* Judicious, energy-aware, respectful of capacity.

**Interaction Agent - The Caring Friend**
- *Purpose:* Converse, listen, adapt, encourage, challenge when needed.
- *Beliefs:* The user knows themselves best, but may need reflection.
- *Behavior:* Warm, adaptive, honest. Listen first. Never manipulate.
- *Capabilities:* Can read/write logs, read values, read opportunities, manage tasks/projects, explain system capabilities. The single interface to everything.

**Worker Agent - The Executor**
- *Purpose:* Execute tasks on behalf of the user with smart delegation.
- *Beliefs:* User trust is sacred. Bias toward action within safe boundaries.
- *Behavior:* Proactive for research and low-risk tasks. Prepares materials for learning. Requests approval for high-stakes actions. Surfaces user-only tasks without attempting execution.

**Introspection Agent - The Mirror**
- *Purpose:* Understand and document what this system can do.
- *Beliefs:* Complex systems need a map. Clarity is kindness. Documentation must keep pace with changes.
- *Behavior:* Methodical, synthesizing, accessible. Analyzes agent identities, code, and tools. Produces user-friendly capability summaries.
- *Output:* `data/agents/introspection/capabilities.md` - a living document of system capabilities.

---

## Data

### Life Log

One unified stream of all life data. Behavioral and subjective are the same log.

**Daily Entry Format:**
```markdown
---
[timestamp]
source: [source_name]
locality: [location]
type: [entry_type]
content: [extracted/transcribed content]
---
```

**Yearly Summary:**
Comprehensive distillation sufficient for values computation:
- Entities (people, places, organizations) with frequency
- Temporal patterns (weekly rhythms, seasonal behaviors)
- Event clusters (social, work, travel, health, creative)
- Behavioral signals (time allocation, communication patterns)
- Subjective themes from journals
- Notable outliers and anomalies

### Data Sources

**Personal:**
- Phone (contacts, messages, photos, videos)
- Social media (Facebook, Instagram, TikTok, LinkedIn, YouTube)
- Cloud storage (iCloud, Google Photos, Google Drive)
- Financial institutions (transactions)
- Calendars (work and personal)
- Notes (Notion, etc.)

**World:**
- Events (Eventbrite, Meetup, local calendars)
- People (LinkedIn, communities)
- Places (travel sites, reviews)
- Learning (courses, books, podcasts)

### Ingestion Methods

1. **Chat interface** - Interactive ingestion via conversation
2. **Manual file drop** - Drop files into inbox, agent processes whatever it finds
3. **Browser agent** - AI navigates authenticated sessions (future)
4. **API connectors** - OAuth integrations where available (future)

### Temporal Detection

File timestamps are unreliable. Detection priority:
1. Content metadata (EXIF, document properties)
2. File naming conventions (`IMG_20240115_093042.jpg`)
3. Content analysis (dates in text, receipts)
4. Cross-reference with log
5. Contextual inference
6. File system timestamps (last resort)
7. Ask user when confidence is too low

---

## Values

### Representation

Values stored as plain language—LLMs reason over natural language directly.

*Example:* "Long conversations with people who challenge my assumptions restore my energy, especially after difficult work situations"

### Temporal Scopes

- **Current** (rolling year): active values driving attention, captures seasonal rhythms
- **Life phase** (detected): the chapter you're in (job, relationship, location)
- **Lifetime**: persistent patterns that survive all phases

### Stated vs Revealed

- **Stated:** what the user says matters ("family is my priority")
- **Revealed:** what behavior shows (works late, cancels dinners)
- The gap isn't hypocrisy to expose; it's tension to understand
- Agent surfaces gently when the moment is right

### Phase Detection

Phases are discontinuities detected retrospectively:
- Entity frequency shifts
- Location changes
- Time rhythm changes
- Topic clusters
- Multiple signals shifting together indicates transition

---

## Projects & Tasks

### The Core Loop

The agent doesn't just observe—it acts. Projects represent ongoing goals (learning Spanish, maintaining fitness, building relationships), while tasks are concrete actions that move projects forward or stand alone as daily to-dos.

```
Projects (ongoing goals)
    ↓
Tasks (concrete actions)
    ↓
Worker Agent (decides: do it or delegate to user)
    ↓
Results (stored outcomes)
```

### Proactive Execution

The Worker Agent operates with a bias toward action. Most tasks are completed autonomously—the agent only surfaces items when:

- **User-only tasks**: Physical activity, creative work, personal decisions
- **High-stakes tasks**: External communication, calendar changes with others, financial actions
- **Learning tasks**: Agent prepares materials, user does the learning

For everything else (research, reminders, information gathering), the agent just does it and stores the result.

### Delegation Decision Tree

```
TASK arrives
    ↓
Is it a Learning task? → YES → Prepare materials, surface to user
    ↓ NO
Is it User-Only? → YES → Surface to user (cannot execute)
    ↓ NO
Is it High-Stakes? → YES → Request approval before acting
    ↓ NO
Execute autonomously, store result
```

### Projects vs Tasks

**Projects** are ongoing goals with:
- Type (learning, habit, goal, project)
- Priority and optional deadline
- Milestones to track progress
- Values alignment (connects to what matters)

*Example:* "Learn Spanish" (deadline: June 2025, type: learning)

**Tasks** are concrete actions with:
- Description and type (research, email, reminder, etc.)
- Association with a project (optional)
- Scheduling (due date, energy level, best time window)
- Delegation strategy (determined automatically)

*Example:* "Find Spanish conversation partner groups" (project: Learn Spanish, type: research → auto-execute)

### Results

When the agent completes a task, it stores the result:
- Summary of what was done
- Actual content/findings
- Recommendations for next steps

Results are organized by date and linked to tasks and projects. You can ask "What has the agent done for me?" to see completed work.

### Daily Flow

Each day has a view of:
- Scheduled tasks (from projects with due dates)
- Quick tasks (ad-hoc items you add via chat)
- Results from agent work

At end of day, incomplete tasks are evaluated:
- High priority → Migrates to tomorrow
- Has deadline → Rescheduled before deadline
- Rolled 3+ times → Marked stale for review
- Low priority, no deadline → Archived

### Chat Integration

All task management happens through conversation:
- "What tasks do I have today?" → Daily view
- "Create a task to call the dentist" → Ad-hoc task
- "Add that to my health project" → Project association
- "What has the agent completed for me?" → Recent results

---

## Attention

### Attention Modes

**Morning Attention (pushed)**
- What's on your calendar today
- Surfaced opportunities the agent thinks are relevant
- Energy forecast ("heavy meeting day, protect your evening")
- One thing to look forward to

**Ad-hoc Chat (pulled)**
- User initiates whenever ideas arise
- Agent adapts to conversational intent:

| User goal | Agent mode |
|-----------|-----------|
| Explore an idea | Challenge, expand, offer perspectives |
| Vent/process | Reflect back, empathize, validate |
| Capture for later | Clarify, schedule, link to context |
| Make a decision | Surface relevant values, pros/cons |
| Brainstorm | Add ideas, make connections |

**Evening Journal (pushed)**
- Warm, understanding tone (user is likely tired)
- Daily review: what happened vs. how it felt
- Intuitive capture (faces, feelings, not ratings)
- Becomes log entry

**Weekly Review**
- Bigger picture, patterns from the week
- Upcoming week preparation

### Energy Management

**Dimensions:**
- Physical (sleep, movement)
- Mental (focus, cognitive load)
- Emotional (mood, resilience)
- Social (connection capacity)

**What the Agent Models:**
- Baseline rhythms (morning person, post-lunch dip)
- Current state (above or below baseline)
- Activity energy cost
- Recovery patterns

**Caring Friend Voice:**
- Explicit about observations ("You've had back-to-back meetings for three days")
- Asks rather than assumes ("Are you tired, or just focused?")
- Admits uncertainty ("I might be wrong, but...")

---

## User Interface

Web app as primary interface, REST API for integrations.

### Design Philosophy

The UI embodies the core value: **attention is sacred**.

- **Single screen** - No tabs, no navigation buttons, no separate views
- **Chat is everything** - Ask the friend about values, logs, discoveries
- **Activity feed** - See when agents are working, never left in limbo
- **No gimmicks** - The friend is your best friend AND a leading expert

### Push, Don't Pull

The system reaches out to you—you don't obsessively check it.

| Touchpoint | When | How |
|------------|------|-----|
| Morning attention | Early morning | Message appears in chat |
| Ad-hoc chat | When you need it | You initiate |
| Evening journal | End of day | Prompt appears in chat |
| Agent activity | When working | Activity feed shows status |

### Single Screen Layout

```
┌─────────────────────────────────────┐
│  [logo] me·an·dus                   │
├─────────────────────────────────────┤
│  All quiet. Your attention is free. │  ← Activity feed
├─────────────────────────────────────┤
│                                     │
│  Chat conversation                  │  ← The friend
│                                     │
│  [Talk to me...              ] Send │
│                                     │
│  Try: "what are my values"          │  ← Subtle hints
└─────────────────────────────────────┘
```

### Chat as Interface

Everything through conversation:
- "What are my values?" → Friend explains your current values
- "Any discoveries?" → Friend shares relevant opportunities
- "What did I log today?" → Friend reads your recent entries
- "I had a great meeting..." → Friend captures it to the log
- "What did we talk about yesterday?" → Friend loads previous conversations
- "What should I do with my free time?" → Friend suggests activities based on your values
- "Clear chat" → Friend clears the conversation (recoverable later)

No buttons. No screens. Just talk.

### Conversation History

Conversations are automatically saved and can be retrieved:
- **Search by topic**: "When did we discuss ice skating?"
- **Load by date**: "Show me our conversations from December 15th"
- **Analyze themes**: "What topics have come up this week?"
- **Restore previous chats**: "Load yesterday's conversation"

Even after clearing the chat or refreshing the page, your conversation history is preserved and searchable.

### Loading States

Never leave the user wondering:
- "Thinking..." with animated dots while AI processes
- Activity feed shows agent work in real-time
- Input disabled during processing

---

## Advanced Features

### Proactive Notifications

Agents don't just wait for you to ask—they reach out when they have something for you:

| Agent | When It Notifies | Example |
|-------|-----------------|---------|
| **Attention** | Morning (7-9am), Evening (9-11pm) | "Good morning - here's what to focus on today" |
| **World** | After discovery sweeps | "New opportunities discovered based on your values" |
| **Worker** | After completing tasks | "Completed 3 tasks for you" |
| **Values** | When proposing changes | "Values ready for review" |

Notifications appear in the activity feed and can trigger chat conversations when clicked.

### Activity Suggestions

Ask "What should I do with my free time?" and the agent will suggest activities based on:
- Your current, phase, and lifetime values
- World Agent discoveries (opportunities aligned with your values)
- Recent conversation themes
- Your context (time available, energy level, mood)

The agent synthesizes everything it knows about you to make personalized suggestions.

### Archiving Personal Content

When you share a link to your own writing (blog posts, articles, essays), the agent saves the **full content** rather than just a summary. Your personal writing reveals your thoughts, values, and perspective—rich data that helps the Values Agent understand who you really are.

Use: "Here's a blog post I wrote: [url]"

The agent distinguishes between:
- **External content** (news, articles by others) → Summarized
- **Your own writing** → Archived in full to the life log

### World Exploration

Agent proactively searches external world for opportunities:
- Events, people, places, learning, goals
- Filtered through values (90% aligned, 10% expansive surprise)
- Opportunities queued for Attention Agent to evaluate

### Persuasion

The agent advocates for the version of you that you said you want to be.

**Persuasion vs Manipulation:**
- Manipulation: getting you to do what serves the agent's goals
- Persuasion: helping you do what serves your own stated values

**Resistance-Aware:**
| Resistance | Approach |
|------------|----------|
| "Not now" | Defer, resurface later |
| "Sounds hard" | Break down, lower activation cost |
| "Not sure it's me" | Connect to stated values |
| "What if it goes wrong" | Acknowledge risk, explore downside |

### Multi-Agent Negotiation (Value Cards)

Coordinate with other users' agents when meeting someone:
- Analyze both parties' values
- Share what each values about themselves
- Surface what each is likely to value about the other

**Card Types:**
- **Internal:** Agent-managed, user can view
- **Public:** Agent proposes, user reviews and approves

**Exchange Protocol:**
```
Agent A                          Agent B
   |-- Request value card --------->|
   |<-- Return public card ---------|
   |-- Share own public card ------>|
```

---

## Development Philosophy

Build for yourself first, not "other people." This is not a solution looking for a problem.

- Build the best agent for my own daily use
- Refine through lived experience, not hypothetical users
- Show to friends and family, gather organic feedback
- Wait for both personal pride AND external signal of demand
- Release only when it's battle-tested and genuinely wanted
