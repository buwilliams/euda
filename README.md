# Me and Us

An AI personal assistant that curates my attention to maximize the wonder of being alive. It learns what promotes life for me—joy, growth, connection, contribution—by observing my logged life and forming conjectural values. It proactively explores the world for opportunities, advocates for experiences I might resist, and manages my energy to surface the right things at the right time.

## Philosophy

The agent needs a philosophical foundation to operate. Users define their own, but here's a starting point:

- Absolute knowledge is impossible; all knowledge is conjecture (Popper)
- In absence of perfect knowledge, we make our own meaning
- Meaning is found in life: motion, growth, pleasure, joy, peace, awe
- Values are beliefs/predictions about what promotes life and happiness
- Values are not fatalist truths but useful generalizations that can be refined or discarded

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

- How sources connect, sync patterns, backfill handling
- [TO BE DEFINED]

## Attention

- The agent monitors activities for completion, prioritization, scheduling, and deprecation
- Time optimization across past (gratitude/reflection), present (preparedness), future (planning)
- The agent should increase the joy of being alive, help reach goals, contribute to world and community

### Attention Modes

- Morning attention: daily briefing, high-energy decisions, action-oriented
- Ad-hoc: on-demand review when user requests
- Evening journal: reflection, subjective experience capture, low-energy appropriate
- [TO BE DEFINED]

### Energy Management

- Model daily energy rhythms and current energy state
- Time suggestions based on energy cost and user capacity
- Understand when to push vs. when to defer
- [TO BE DEFINED]

## World Exploration

- Agent proactively searches external world for opportunities matching values
- People to meet, events to attend, places to visit, things to learn, goals to pursue
- Not passive; actively discovers and proposes
- [TO BE DEFINED]

## Persuasion

- Body defaults to energy conservation; user will resist change
- Agent must advocate, not just inform
- Frame opportunities to overcome specific resistance
- Build trust through track record; successful recommendations earn credibility
- [TO BE DEFINED]

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
