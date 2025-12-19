# Me and Us

An AI personal assistant that curates my attention to maximize the wonder of being alive. It learns what promotes life for me—joy, growth, connection, contribution—by observing my logged life and forming conjectural values. It proactively explores the world for opportunities, advocates for experiences I might resist, and manages my energy to surface the right things at the right time.

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
6. I can ad-hoc request a review for my daily attention

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
    [yyyy-mm-dd].txt   # daily log entries
    _manifest.txt      # tracks completeness, sources, processing state
    _summary.txt       # comprehensive yearly distillation
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
  notes.txt
```

- Agent watches directory, identifies file types, extracts content
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
- [TO BE DEFINED]

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
- [TO BE DEFINED]

## User Interface

- Web app as primary interface
- REST API for integrations
- Calendar integration to prompt user to open web app
- [TO BE DEFINED]
