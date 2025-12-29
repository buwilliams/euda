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
- A record of constraints, tendencies, and tradeoffs
- A snapshot of how a person navigates the world at a point in time

Profiles are expected to evolve.

---

## Profile Variants

There are two profile variants:

### Private Profile
- Source of truth
- May include sensitive, vulnerable, or identifying information
- Used internally by Euno agents
- Stored as:
  - `profile.current.md`
  - `profile.YYYY.md`

### Public Profile
- Derived artifact
- Selected and written intentionally for sharing
- Must follow public-sharing principles
- Stored as:
  - `profile.public.current.md`
  - `profile.public.YYYY.md`

Public profiles are **not redacted private profiles**.
They are **new compositions**, written under explicit principles and user preferences.

---

## Profile Frontmatter (Required)

Every profile file MUST begin with JSON frontmatter:

```json
{
  "profile_version": "1.0",
  "scope": "private | public",
  "generated_at": "YYYY-MM-DDTHH:MM:SSZ",
  "user_id": "<optional>",
  "source_profile": "<path>"
}
```

The frontmatter block is delimited by triple backticks with `json` language marker at the start of the file.

Fields:
- `profile_version`: Contract version (currently "1.0")
- `scope`: Either "private" or "public"
- `generated_at`: ISO 8601 timestamp of generation
- `user_id`: Optional identifier for multi-user scenarios
- `source_profile`: Required for public profiles; path to the private source

---

## Canonical Section Order

Profiles MUST follow this section order:

1. **Identity Constraints** — Non-negotiable rules revealed by sacrifice and refusal
2. **Failure Modes** — Predictable breakdowns under stress
3. **Behavioral Attractors** — Stable patterns across contexts
4. **Utility Tradeoff Curves** — What gets sacrificed first when goals conflict
5. **Epistemic Style** — How uncertainty, revision, and authority are handled
6. **Narrative Identity** — Self-concept and aspirational framing

Agents may omit empty sections but may not reorder or rename them.

---

## Canonical Definitions

These definitions are authoritative across all agents:

### Identity Constraint
A rule revealed by what the person will suffer rather than violate.
- Not a preference or value statement
- Derived from observed sacrifice or refusal
- Rarely changes; when it does, it signals deep shift

### Failure Mode
A predictable pattern of breakdown under specific conditions.
- Describes the trigger, the behavior, and the consequence
- Strongest behavior predictor under stress
- Phrased descriptively, not judgmentally

### Behavioral Attractor
A stable pattern the person returns to across contexts.
- Observable regularity, not aspiration
- May be positive, negative, or neutral
- Persists over time despite variation

### Utility Tradeoff Curve
What the person sacrifices first when goals conflict.
- Reveals operative priorities (truth vs. belonging, comfort vs. dignity)
- Inferred from actual choices, not stated preferences

### Epistemic Style
How the person handles uncertainty, revision, and authority.
- Approach to changing beliefs
- Relationship to expertise and evidence
- Comfort with ambiguity

### Narrative Identity
The story the person tells about themselves.
- Self-concept and aspirational framing
- Useful for alignment, unreliable for prediction
- May diverge from operative behavior

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
5. **Third-party identifying information** — Names, relationships, or details about others without their consent
6. **Precise location data** — Specific addresses, coordinates, or identifying places
7. **Financial details** — Exact amounts, account information, or transaction records
8. **Health specifics** — Diagnoses, medications, or detailed medical information

These constraints are **structural**, not content-detection-based.
They are enforced by artifact-class boundaries in the generation pipeline.

---

## Time-Indexed Evolution Rules

### Current Profiles
- `profile.current.md` — Always the latest private profile
- `profile.public.current.md` — Always the latest public profile

### Annual Snapshots
- `profile.YYYY.md` — Private profile as of that year
- `profile.public.YYYY.md` — Public profile as of that year

### Writing Rules
When a new private profile is generated:
1. Overwrite `profile.current.md`
2. Overwrite `profile.YYYY.md` (year from `generated_at`)

When a new public profile is generated:
1. Overwrite `profile.public.current.md`
2. Overwrite `profile.public.YYYY.md` (year from `generated_at`)

### Immutability
Historical profiles (previous years) are never mutated.
Only the current year's snapshot may be overwritten.

---

## Guiding Principle

**Structure over story, omission over exposure.**

When deciding what belongs in a profile:
- Prefer structural patterns over narrative descriptions
- Prefer evidence pointers over excerpts
- Prefer omission over uncertain exposure
- Prefer abstraction over specificity for public profiles

A profile that says too little is safer than one that says too much.
A profile that shows structure is more useful than one that tells stories.

---

## Validation Requirements

A valid profile:
1. Has correct YAML frontmatter with required fields
2. Contains sections in canonical order (may omit empty sections)
3. Uses the profile item microformat where applicable
4. Contains no forbidden artifact types (public only)

Validation is **structural**, not semantic.
The validator checks form, not meaning.
LLMs are responsible for content judgment.

---

## References

- `redaction.policy.md` — Plain-language sharing principles
- `share.prefs.current.md` — User-specific sharing preferences

This contract is authoritative. All profile-producing agents must reference it.
