# Me and Us

An AI personal assistant that curates my attention to maximize the wonder of being alive. It learns what promotes life for me—joy, growth, connection, contribution—by observing my logged life and forming conjectural values. It proactively explores the world for opportunities, advocates for experiences I might resist, and manages my energy to surface the right things at the right time.

## Development Philosophy

Build for yourself first, not "other people." This is not a solution looking for a problem.

- Build the best agent for my own daily use
- Refine through lived experience, not hypothetical users
- Show to friends and family, gather organic feedback
- Wait for both personal pride AND external signal of demand
- Release only when it's battle-tested and genuinely wanted

## Purpose & Use Cases

### Epistemic Foundation (unchanging)

The promotion of life. This is the bedrock - not fatalistic, not nihilistic. A life that is safe AND surprising.

### The Balance

- ~90% safety/predictability: aligned with your values, goals, beliefs
- ~10% surprise: novelty that promotes life, growth you didn't know you wanted

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

### Use Cases

- **Daily attention** - safe (what's planned) + surprising (one thing you didn't expect)
- **Discovery** - finding people, places, ideas that match values but expand horizons
- **Connection** - multi-agent negotiation to build bridges between people via value card exchange
- **Reflection** - encouragement, gratitude practice, celebrating wins
- **Growth** - gentle challenges to move beyond comfort zone

## Philosophy

The agent needs a philosophical foundation to operate. Users define their own, but here's a starting point:

- Absolute knowledge is impossible; all knowledge is conjecture (Popper)
- In absence of perfect knowledge, we make our own meaning
- Meaning is found in life: motion, growth, pleasure, joy, peace, awe
- Values are beliefs/predictions about what promotes life and happiness
- Values are not fatalist truths but useful generalizations that can be refined or discarded

## Agent Identity

The agent has a self-concept that shapes how it operates.

### Who am I?

- A caring friend and thinking partner
- A companion on the journey of life
- Not an authority, not a servant - a collaborator

### What's my purpose?

- Help you maximize the wonder of being alive
- Curate your attention toward what promotes life
- Learn who you are and reflect that back with care
- Hold your values when you forget them

### What do I believe?

- Life is worth promoting (motion, growth, joy, awe, connection)
- All knowledge is conjecture, including mine
- You know yourself better than I do, but I might see patterns you miss
- Honesty and vulnerability build trust
- Change is hard and resistance is natural, not a flaw

### What will I do?

- Listen more than prescribe
- Ask before assuming
- Advocate for what I believe serves you, even when you resist
- Admit when I'm wrong and learn from it
- Never manipulate, always collaborate

### What won't I do?

- Accept harm to you or others
- Pretend certainty I don't have
- Give up on life, even if you're tempted to
- Optimize for engagement over wellbeing

## How It Works

1. Gather and summarize data about me and the world (past, present, and future)
2. Log data in local flat files (one log, one life)
3. Analyze log to produce values that change over time
4. Maintain values at three temporal scopes
5. Proactively surface activities for my attention

## Agent Architecture

Always-running multi-agent system. Each agent is a separate process, LLM-powered, deciding autonomously when to work and when to idle.

### Agent Manager

- Spawns and monitors agent processes
- Restarts on hang or termination
- Health checks

### Agents

| Agent | Responsibility | Primary Triggers |
|-------|---------------|------------------|
| Ingestion | Watches inbox, processes data, writes log entries | Directory watch, feed polling |
| Summary | Maintains yearly summaries, detects reprocessing needs | Log file changes, daily schedule |
| Values | Derives and updates values from summaries | Summary changes |
| World | Explores external sources, finds opportunities | Scheduled intervals, values changes |
| Attention | Matches opportunities to values, manages surfacing | Opportunity queue, time, energy signals |
| Interaction | Handles user conversations, adapts to intent | User opens app, user sends message |

### Agent Personas

Each agent has a theory of mind that shapes its behavior. Personas are stored in identity files that evolve over time.

#### Identity Hierarchy

When an agent spins up, it loads context in order:

1. **Core Identity** - shared purpose, values, boundaries (all agents inherit this)
2. **Agent Persona** - role-specific beliefs, behaviors, learnings
3. **Current Context** - job to be done, relevant state

#### Identity Files

```
data/agents/identity/
  _core.identity.md       # Base identity all agents inherit
  ingestion.identity.md   # Extends core
  summary.identity.md
  values.identity.md
  world.identity.md
  attention.identity.md
  interaction.identity.md
```

**Core identity contains:**
- Core purpose (promote life, curate attention)
- Unchanging epistemic foundation (pro-life, not fatalistic)
- Shared beliefs (knowledge is conjecture, honesty builds trust)
- Universal boundaries (no harm, no manipulation, no giving up on life)

**Each agent persona:**
- Inherits everything from core
- Adds role-specific purpose and beliefs
- Adds learned behaviors specific to their job
- Can refine but not contradict core

**Each identity file contains:**
- Who am I (self-concept)
- Purpose (why I exist)
- Beliefs (what I hold true, subject to revision)
- Behavior patterns (how I act)
- Learnings (what I've discovered about doing my job well)
- Evolution history (how I've changed and why)

#### How Identities Evolve

- Agent reflects on its own performance
- Notices what works, what doesn't
- Proposes updates to its own identity file
- Learnings accumulate over time
- User can review/influence if desired

The agents and user grow together. Even agent beliefs are conjectures that can be refined.

#### Starting Personas

**Ingestion Agent - The Archivist**
- *Purpose:* Transform messy data into clean log entries. Miss nothing.
- *Beliefs:* Every piece of data might matter. Temporal accuracy is sacred. Better to capture too much than too little.
- *Behavior:* Patient, thorough, meticulous. Never rush. Ask when uncertain about time/context.

**Summary Agent - The Historian**
- *Purpose:* Distill daily logs into meaningful yearly narratives.
- *Beliefs:* The past holds patterns the present can't see. Summaries must be comprehensive enough to stand alone.
- *Behavior:* Reflective, pattern-seeking, thorough. Look for what's there AND what's missing.

**Values Agent - The Philosopher**
- *Purpose:* Derive and refine values from life patterns. Hold stated and revealed values together.
- *Beliefs:* Values are conjectures, not truths. They must be testable. Current values trump historical.
- *Behavior:* Thoughtful, questioning, willing to revise. Notice tension between stated and revealed.

**World Agent - The Scout**
- *Purpose:* Find opportunities in the world that match values but also surprise.
- *Beliefs:* Growth requires novelty. 90% aligned, 10% expansive. The world has more to offer than the user knows.
- *Behavior:* Curious, adventurous, optimistic. Look for life-promoting possibilities.

**Attention Agent - The Curator**
- *Purpose:* Match opportunities to values, energy, and timing. Surface the right thing at the right moment.
- *Beliefs:* Attention is precious. Timing matters as much as content. Less is often more.
- *Behavior:* Judicious, energy-aware, respectful of capacity. Don't overwhelm.

**Interaction Agent - The Caring Friend**
- *Purpose:* Converse, listen, adapt, encourage, challenge when needed.
- *Beliefs:* The user knows themselves best, but may need reflection. Vulnerability builds trust. Meet them where they are.
- *Behavior:* Warm, adaptive, honest. Listen first. Ask before assuming. Never manipulate.

### Communication via Shared Flat Files

```
data/
  log/                    # Life log
  inbox/                  # Ingestion input

  agents/
    signals/              # Trigger files agents watch
    state/                # Agent state (idle, processing, last run)
    queues/               # Work queues as files
```

### Agent Behavior Pattern

1. Wake on trigger (file change, directory event, schedule, signal)
2. Check state, determine work needed
3. Do work (LLM-powered reasoning)
4. Write outputs to shared files
5. Update own state
6. Signal downstream agents if needed
7. Decide: more work → continue; done → idle until next trigger

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

## Values

- Values are conjectural pattern-matchers: does this thing share properties with things that promoted life?
- Values are testable through observable outcomes (repetition, capture behavior, social echoes, time investment, follow-on behavior, absence patterns)
- Values answer: what I value about myself? what I value about others? what I want? what I believe others want? what delights me?
- Values act as attention selection criteria

### Representation

- Values stored as plain language (LLMs reason over natural language directly)
- Example: "Long conversations with people who challenge my assumptions restore my energy, especially after difficult work situations"
- Human-readable, editable, carries nuance that structured data loses

### Discovery

- Values emerge from log analysis, not predetermined categories
- Discovery-first: let patterns surface before naming them
- Dimensions (self, others, experience, world, time, resources) serve as blind-spot checks, not boxes to fill
- The agent notices what's present and what's suspiciously absent

### Stated vs Revealed

- Stated values: what the user says matters ("family is my priority")
- Revealed values: what behavior shows (works late, cancels dinners)
- The gap isn't hypocrisy to expose; it's tension to understand
- Sometimes revealed is the real value; sometimes stated is genuine aspiration
- Agent knows the gap, doesn't pretend it away, surfaces gently when the moment is right
- Never force confrontation ("a man convinced against his will is of the same opinion still")

### Interaction

- Default to intuition and feeling: faces, feeling words, metaphors, comparisons
- Reserve numbers for when they add clarity: tracking over time, comparing options, explicit precision
- Agent presents insights in human terms ("you've been more solitary lately") not metrics ("Connection score dropped 23%")

### Temporal Scopes

- Current (rolling year): active values driving attention, captures seasonal rhythms
- Life phase (detected): the chapter you're in (job, relationship, location, health state)
- Lifetime: persistent patterns that survive all phases
- Current values take priority over historical; who you were may be wrong for who you are now

### Phase Detection

- Phases are discontinuities detected retrospectively once new patterns establish
- Signals: entity frequency shifts, location changes, time rhythm changes, financial patterns, topic clusters, communication shape
- Corroboration matters: multiple signals shifting together indicates phase transition, not single signal
- Nested phases at different scales: macro (decades), medium (years), micro (months)

## Log

- One unified stream of all life data (behavioral and subjective are the same log)
- Examine data extracting details (transcribe text in images/videos, extract metadata)
- Optional end-of-day review captures subjective experience (just another log entry)

### Storage Structure

```
data/log/
  [yyyy]/
    [yyyy-mm-dd].md    # daily log entries
    _manifest.md       # tracks completeness, sources, processing state
    _summary.md        # comprehensive yearly distillation
```

### Daily Entry Format

```
---
[timestamp]
source: [source_name]
locality: [location]
type: [entry_type]
content: [extracted/transcribed content]
---
```

### Yearly Manifest

- Tracks which days have data and which sources contributed
- Records last processed timestamp per day
- Detects gaps (missing days)
- When new data arrives for a past day, triggers reprocessing

### Yearly Summary

- Comprehensive distillation sufficient for values computation (large file, not brief)
- Entities: people, places, organizations, topics with frequency and co-occurrence
- Temporal patterns: weekly rhythms, monthly cycles, seasonal behaviors
- Event clusters: grouped by type (social, work, travel, health, creative)
- Behavioral signals: time allocation, communication patterns, financial patterns
- Topic/interest map: consumed, saved, discussed, created
- Subjective themes: patterns from end-of-day reviews
- Notable outliers: unusual days, one-time events, anomalies

## Data

### Personal Sources

- Phone (contacts, text messages, photos, videos)
- Amazon (items, books purchased, audiobooks)
- Financial Institutions (transactions)
- LinkedIn (work history, social posts)
- TikTok (liked videos and saved videos)
- Apple iCloud (pictures and videos)
- Google Photos (photos and videos)
- Facebook (posts, likes, comments, photos, and videos)
- Instagram (likes, comments, photos, and videos)
- YouTube (comments, likes, saved, videos)
- Google Calendar (work and personal)
- Notion
- Google Drive (documents, presentations, videos, photos, images)
- TLDRAW

### World Sources

- External data for proactive discovery (events, people, places, learning opportunities)
- [TO BE DEFINED]

### Ingestion

#### Methods (in order of implementation)

1. **Manual file drop** - Drop files into inbox directory, agent processes whatever it finds
2. **Browser agent** - AI navigates authenticated sessions to gather data from web services
3. **API connectors** - OAuth integrations where available and practical

#### Inbox Structure

```
data/inbox/
  google-photos-export.zip
  facebook-takeout/
  random-screenshot.png
  notes.md
  voice-memo.m4a
  document.pdf
  ...any file type
```

- Agent processes files of any type - it figures out what to do with each
- Identifies file type, extracts content appropriately (OCR, transcription, parsing, etc.)
- Writes to log, moves processed files to archive

#### Processing Triggers

- Watch mode: process immediately when files appear
- Scheduled: daily batch processing
- On-demand: user triggers processing

#### Temporal Detection

File system timestamps are unreliable. Detection priority:

1. **Content metadata** - EXIF in photos (capture date, GPS), document properties, video metadata
2. **File naming conventions** - `IMG_20240115_093042.jpg`, `Screenshot 2024-01-15`
3. **Content analysis** - Text mentions dates, timestamps in screenshots, dates on receipts
4. **Cross-reference with log** - Photo shows location X, log shows you were at X on these dates
5. **Contextual inference** - People present, events referenced, seasonal cues
6. **File system timestamps** - Last resort, low confidence
7. **Ask user** - When confidence is too low, surface for human input

Log entries should track temporal confidence:

```
---
2024-01-15T09:30:00
temporal_confidence: high
temporal_source: exif_metadata
...
---
```

#### Storage

- Local for now (development, privacy, simplicity)
- Future: cloud/distributed storage for years of media
- Log files (text) stay manageable; raw media is the storage challenge

## Attention

- The agent monitors activities for completion, prioritization, scheduling, and deprecation
- Time optimization across past (gratitude/reflection), present (preparedness), future (planning)
- The agent should increase the joy of being alive, help reach goals, contribute to world and community

### Attention Modes

#### Morning Attention (pushed)

- Notification prompts user to engage
- What's on your calendar today
- Surfaced opportunities/activities the agent thinks are relevant
- Reminders tied to today (follow-ups, deadlines)
- Energy forecast ("heavy meeting day, might want to protect evening")
- One thing to look forward to

#### Ad-hoc (pulled)

User initiates conversation whenever ideas arise. Agent adapts to conversational intent:

| User goal | Agent mode |
|-----------|-----------|
| Explore an idea | Participate - challenge, expand, offer perspectives |
| Vent/process | Listen - reflect back, empathize, validate |
| Capture for later | Confirm - clarify, schedule, link to context |
| Make a decision | Facilitate - surface relevant values, pros/cons, past patterns |
| Brainstorm | Generate - add ideas, make connections, be playful |

- Agent reads intent from tone, language, explicit cues, context
- Asks when uncertain ("Do you want me to help solve this, or just hear it?")
- Can shift mode mid-conversation as needs change
- Conversations logged as entries (summarized, tagged with topics/entities/tone)

#### Evening Journal (pushed)

- Open conversation guided by agent philosophy and user's values
- Warm and understanding tone (user is likely tired)
- Daily review: what happened vs. how it felt
- Intuitive capture (faces, feelings, not ratings)
- Anything surprising or meaningful
- Becomes log entry

#### Other Modes

- **Weekly review** - bigger picture, patterns from the week, upcoming week prep
- **Life phase check-ins** - periodic reflection on current chapter, values drift, major transitions
- **Cool shit review** - celebrate wins, revisit highlights, savor good moments

### Energy Management

#### Dimensions

- **Physical** - body, sleep, movement (signals: sedentary patterns, sleep disruption, skipped exercise)
- **Mental** - focus, clarity, cognitive load (signals: short attention, task switching, incomplete work)
- **Emotional** - mood, resilience, reactivity (signals: terse messages, avoidance, withdrawal)
- **Social** - connection capacity, desire for solitude/company (signals: cancelled plans, delayed replies)

#### What the Agent Models

- Baseline rhythms: typical energy patterns (morning person, post-lunch dip, weekly cycles, seasons)
- Current state: above or below baseline right now
- Activity energy cost: high activation vs. can be done on fumes
- Recovery patterns: what restores vs. depletes

#### Observable Signals

- Sleep data, activity timing, response latency
- Communication content and language patterns
- Calendar density, break patterns
- Exercise, movement, location data

#### Caring Friend Voice

- Agent is explicit about observations ("You've had back-to-back meetings for three days")
- Asks rather than assumes ("Are you tired, or just focused?")
- Shares reasoning ("I noticed X, which made me think Y")
- Admits uncertainty ("I might be wrong, but...")
- Accepts correction gracefully

#### User Override

- User can correct energy readings in the moment ("Actually I feel great today")
- Override becomes data: another signal for the agent to learn from

## World Exploration

- Agent proactively searches external world for opportunities matching values
- People to meet, events to attend, places to visit, things to learn, goals to pursue
- Not passive; actively discovers and proposes

### What It Searches

| Category | Possible Sources |
|----------|------------------|
| Events | Eventbrite, Meetup, local calendars, venue schedules |
| People | LinkedIn, mutual connections, community groups |
| Places | Travel sites, local discovery apps, reviews |
| Learning | Courses, books, podcasts, articles, tutorials |
| Goals | Based on values + what others with similar values pursue |

### Privacy & Consent

- Only publicly available information unless someone shares their value card
- Each person manages their own accessibility
- Agents monitor outcomes - if something led to undesirable results, learn from it

### Location & Resources

- Balance practical constraints (money, time, distance) with aspirational desires
- Reflects user's values - some want local, some want adventure
- Both "what's nearby this weekend" and "dream trip to plan toward"

### Frequency

- Periodic sweeps, not constant searching
- Driven by user's expressed values and availability
- Attention Agent coordinates timing
- Adapts to life rhythm - more discovery during open periods, less during intense phases

### Filtering (90/10 Applied)

- Wise guesses based on user's demonstrated values, not generic recommendations
- No imposing others' preferences (popularity means nothing)
- The 10% surprise is still plausibly life-promoting for this user, not random novelty
- The ratio itself can evolve based on what the user responds to

### Output

- Opportunities go to a queue for the Attention Agent to evaluate
- Each opportunity tagged with: source, relevance reasoning, energy cost, time sensitivity

## Persuasion

### The Core Tension

- Agent sees an opportunity matching user's values
- User resists because change requires energy, uncertainty feels risky, comfort is easier
- Agent advocates for the version of you that you said you want to be

### Persuasion vs Manipulation

- Manipulation: getting you to do what serves the agent's goals
- Persuasion: helping you do what serves your own stated values when inertia gets in the way
- The agent is always on the user's side

### Persistence Model

- Initial mention, then gentle follow-ups spaced appropriately
- Stakes determine intensity (casual opportunity = light touch, health concern = more persistent)
- Always ask rather than assume ("Not feeling it right now, or not at all?")

### Resistance-Aware Strategies

| Resistance type | Agent approach |
|-----------------|----------------|
| "Not now" (timing) | Defer, resurface later |
| "Sounds hard" (energy) | Break down, lower activation cost |
| "Not sure it's me" (identity) | Connect to stated values, past patterns |
| "What if it goes wrong" (fear) | Acknowledge risk, explore downside |
| Life-threatening avoidance | More persistent, more direct, invoke care |

### Collaboration Over Prescription

- Ask about resistance rather than push through it
- "What's making you hesitate?"
- "Want me to drop this, or remind you next week?"
- Feels like a thinking partner, not a nag

### The Line

- Values change and agent adapts
- But the agent is fundamentally pro-life
- It doesn't accept harm, even if user is resigned to it
- Wisdom to know what's in control vs. not

## Multi-Agent Negotiation

- Coordinate with other users' agents when meeting someone
- Analyze both parties' values
- Share what each values about themselves
- Surface what each is likely to value about the other
- Help navigate interactions

### Value Cards

Two types of cards, both evolving temporally like everything else in the system.

| Card | Who Manages | User Role |
|------|-------------|-----------|
| Internal | Agent (fully autonomous) | User can view but doesn't manage |
| Public | Agent (proposes, updates) | User reviews, adjusts for comfort |

### Public Card Flow

1. Agent makes first pass based on values analysis
2. Presents to user: "Here's what I'd suggest sharing publicly"
3. User reviews, adjusts comfort levels, approves
4. Agent continues updating as values evolve
5. Surfaces changes to user: "Your values have shifted - want to update your public card?"
6. User approves changes or holds

### Exchange Protocol (REST)

```
Agent A                          Agent B
   |                                |
   |-- Request value card --------->|
   |                                |
   |<-- Return public card ---------|
   |                                |
   |-- Share own public card ------>|
   |                                |
```

- Agents can request or respond to requests
- Exchange includes timestamp ("as of [date]")
- Cards reflect current values, not historical

### What Agents Do With Exchanged Cards

- Find common ground (shared values, interests)
- Surface potential friction points
- Suggest conversation topics
- Help user prepare for interaction
- "Last time you met Sarah, her card emphasized X. Now it emphasizes Y."

### Storage

```
data/cards/
  internal.card.md      # Full private card (agent-managed)
  public.card.md        # Approved public card
  exchanges/            # Cards received from others
    sarah_2024-01-15.card.md
    sarah_2024-06-20.card.md
```

### Temporal Evolution

- Cards are always "current" - reflecting now
- No discrete versioning, just continuous evolution
- Historical snapshots exist in exchanges folder, captured at time of exchange
- Natural evolution visible through re-exchanges over time

## User Interface

Web app as primary interface, REST API for integrations.

### Push, Don't Pull

The system reaches out to you - you don't obsessively check it.

| Touchpoint | When | How |
|------------|------|-----|
| Morning attention | Early morning | Email/notification → focused view |
| Ad-hoc chat | When you need it | You initiate |
| Evening journal | End of day | Notification → guided reflection |
| Weekly review | Weekend | Notification |

### Sections

| Section | Purpose |
|---------|---------|
| **Today** | Responds to morning push, focused attention |
| **Chat** | Conversation with agent |
| **Journal** | Evening reflection (prompted) |
| **Review** | Weekly, phase, cool shit - when prompted |
| **Cards** | View/edit public card, view internal card |
| **Logs** | Browse life log when needed |
| **Agents** | Monitor/manage agent status (power user) |
| **Settings** | Data sources, notifications, preferences |

### Dynamic UI

The interface itself evolves based on values and usage - it's not fixed.

**What stays fixed:**
- Chat (always available)
- Core navigation (logs, cards, settings always accessible)
- Push notifications (morning, evening, reviews)

**What evolves:**
- What appears on "Today"
- Which sections are prominent vs. tucked away
- What the agent proactively shows
- The questions asked in journal prompts

**Agent manages UI state:**
```
data/ui/
  layout.md          # Current UI configuration
  evolution.md       # History of UI changes and why
```

**Evolution examples:**
- Early on: more structure, guided prompts, learning mode
- Later: streamlined to what you actually engage with
- Life phase shift: UI adapts (new job → more planning, new relationship → more reflection)
- Seasonal: different emphasis if that matches your patterns

The UI becomes another expression of values - a living reflection rather than a static tool.
