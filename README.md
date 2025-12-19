# Me and Us

An AI personal assistant that curates my attention to maximize the wonder of being alive. It learns what promotes life for me—joy, growth, connection, contribution—by observing my logged life and forming conjectural values. It proactively explores the world for opportunities, advocates for experiences I might resist, and manages my energy to surface the right things at the right time.

## Table of Contents

- [Core Concepts](#core-concepts)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Agents](#agents)
- [Data](#data)
- [Values](#values)
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
    signals/                # Inter-agent communication
    state/                  # Agent state (JSON files)
    queues/                 # Work queues

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

### Agent Identity

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

### Push, Don't Pull

The system reaches out to you—you don't obsessively check it.

| Touchpoint | When | How |
|------------|------|-----|
| Morning attention | Early morning | Notification → focused view |
| Ad-hoc chat | When you need it | You initiate |
| Evening journal | End of day | Notification → guided reflection |
| Weekly review | Weekend | Notification |

### Sections

| Section | Purpose |
|---------|---------|
| **Today** | Morning attention, focused view |
| **Chat** | Conversation with agent |
| **Journal** | Evening reflection |
| **Review** | Weekly, phase, celebration |
| **Cards** | View/edit public card, view internal card |
| **Logs** | Browse life log |
| **Agents** | Monitor/manage agent status |
| **Settings** | Data sources, notifications, preferences |

### Dynamic UI

The interface evolves based on values and usage:

**Fixed:** Chat, core navigation, push notifications

**Evolves:** What appears on "Today", which sections are prominent, questions in journal prompts

---

## Advanced Features

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

### Agent Identity

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
