# Profile Contract — Euno

This document defines the Profile Contract for Euno user profiles.

It specifies:
- What a profile is
- How it is structured
- How private and public profiles differ
- What kinds of information are allowed in each
- How profiles evolve over time

This contract is intentionally schema-light:
- Markdown-first
- Human-readable
- Enforced by principles and structure, not rigid databases

All profile-producing agents MUST comply with this contract.

---

## What a Profile Is

A profile is a **living structural model of a person** designed to support anticipation, alignment, and long-term coherence.

A profile is **not**:
- A biography
- A transcript of life events
- A value statement or personal brand
- A complete or authoritative description of the person

A profile **is**:
- A synthesis of recurring patterns
- A record of what a person wants, fears, and returns to
- A snapshot of how a person navigates the world at a point in time

Profiles are expected to evolve.

---

## Cognitive Core

The profile captures identity through the lens of the cognitive core:

1. **Humans act to pursue what they desire and avoid what they fear.**
2. **Early life is dominated by exploration** — trying strategies to learn what works.
3. **Strategies that reliably work are exploited** — repeated, reinforced, cheaper over time.
4. **Repeated exploitation forms stable internal attractors** — patterns the person returns to.
5. **Identity is the pattern of these attractors over time** — not raw desire, values, or stories.
6. **The self-model is a story layered on top of behavior** — useful but incomplete.
7. **Lasting change requires new strategies to work under real conditions.**
8. **Flourishing requires balance** — ~90% exploitation for stability, ~10% bounded exploration.

---

## Profile Variants

There are two profile variants:

### Private Profile
- Source of truth
- May include sensitive, vulnerable, or identifying information
- Used internally by Euno agents
- Stored as:
  - `_profile.current.md` (in lifelog/)
  - `_profile.YYYY.md` (yearly snapshots in lifelog/YYYY/)

### Public Profile
- Derived artifact
- Selected and written intentionally for sharing
- Must follow public-sharing principles (see redaction.policy.md)
- Stored as:
  - `_profile.public.md`

Public profiles are **not redacted private profiles**.
They are **new compositions**, written under explicit principles and user preferences.

---

## Canonical Section Order

Profiles MUST follow this section order:

1. **Biographical Information** — Name, addresses, phone numbers, etc.
2. **Wants and Fears** — Patterns of behavior that uncover desires and fears
3. **Stable Attractors** — Patterns the person returns to
4. **Notable Events and Actions** — Either because they are consistent or surprising
5. **Influences** — People, places, books, activities, entertainment, trips, experiences
6. **Interests** — Goals, projects, work, hobbies, entertainment
7. **Summary of Changes** — From previous years (current profile only)

Agents may omit empty sections but may not reorder or rename them.

---

## Canonical Definitions

These definitions are authoritative across all agents:

### Biographical Information
Factual identifying data about the person.
- Name, addresses, contact information
- Key dates (birth, relationships, career milestones)
- Basic demographics where relevant

### Wants and Fears
Patterns of behavior that reveal underlying desires and fears.
- Not stated preferences — inferred from actions
- What the person pursues repeatedly
- What the person avoids or resists
- Derived from observed behavior, not self-report

### Stable Attractors
Patterns the person returns to across contexts and time.
- Observable regularities, not aspirations
- Behavioral defaults under stress
- Strategies that have become cheap and familiar
- May be positive, negative, or neutral

### Notable Events and Actions
Significant moments that reveal identity.
- Consistent behaviors that confirm patterns
- Surprising actions that challenge or update understanding
- Decisions under pressure that reveal priorities
- Evidence of change or stability

### Influences
External factors that have shaped the person.
- People: mentors, family, friends, role models
- Places: cities, institutions, environments
- Media: books, films, music, art
- Experiences: travel, education, challenges, achievements

### Interests
Current areas of engagement and aspiration.
- Goals: what they're working toward
- Projects: active endeavors
- Work: professional focus
- Hobbies and entertainment: how they spend discretionary time

### Summary of Changes
Evolution from previous years (current profile only).
- What has shifted since the last profile
- New patterns that have emerged
- Old patterns that have faded
- Significant life transitions

---

## Profile Item Microformat

Each item within a section SHOULD follow this format:

```markdown
- **[Label]**: [Description]
  - Evidence: [pointer to source, not excerpt]
  - Confidence: [high | medium | low]
  - Last observed: [YYYY or YYYY-MM]
```

Example:

```markdown
- **Prefers solitude under stress**: Withdraws to process rather than seeking support
  - Evidence: lifelog/2024/2024-11-15.md
  - Confidence: high
  - Last observed: 2024-11
```

Rules:
- Evidence is a **pointer**, not an excerpt or quote
- Confidence reflects how well-established the pattern is
- Last observed helps track currency

---

## Public Profile Hard Constraints

Public profiles MUST NOT contain:

1. **Raw logs** — Unprocessed diary entries, transcripts, or stream-of-consciousness
2. **Direct quotes** — Verbatim speech or writing from private sources
3. **Transcripts** — Conversation records, message threads, or chat logs
4. **Excerpts** — Partial reproductions of private documents
5. **Third-party identifying information** — Names, relationships, or details about others without consent
6. **Precise location data** — Specific addresses, coordinates, or identifying places
7. **Financial details** — Exact amounts, account information, or transaction records
8. **Health specifics** — Diagnoses, medications, or detailed medical information

These constraints are **structural**, not content-detection-based.
They are enforced by artifact-class boundaries in the generation pipeline.

---

## Time-Indexed Evolution Rules

### Current Profile
- `_profile.current.md` — Always the latest private profile
- `_profile.public.md` — Always the latest public profile

### Annual Snapshots
- `_profile.YYYY.md` — Private profile as of that year

### Writing Rules
When a new private profile is generated:
1. Overwrite `_profile.current.md`
2. Overwrite `_profile.YYYY.md` (year from generation date)

### Immutability
Historical profiles (previous years) are never mutated.
Only the current year's snapshot may be overwritten.

---

## Guiding Principle

**Behavior over statements, patterns over incidents.**

When constructing a profile:
- Prefer observed behavior over stated preferences
- Prefer recurring patterns over single incidents
- Prefer evidence pointers over excerpts
- Prefer omission over uncertain inclusion

A profile that says too little is safer than one that says too much.
A profile that shows patterns is more useful than one that tells stories.

---

## Validation Requirements

A valid profile:
1. Contains sections in canonical order (may omit empty sections)
2. Uses the profile item microformat where applicable
3. Contains no forbidden artifact types (public only)
4. Derives claims from observed behavior, not self-report alone

Validation is **structural**, not semantic.
The validator checks form, not meaning.
LLMs are responsible for content judgment.

---

## References

- `redaction.policy.md` — Plain-language sharing principles for public profiles
- `docs/2_profile.md` — Authoritative specification for cognitive core and profile schema

This contract is authoritative. All profile-producing agents must reference it.
