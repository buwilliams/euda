# Anticipate

Euno is "a personal intelligence that anticipates you." This document defines how we achieve anticipation through two complementary systems: **Profile** and **Memory**.

- **Profile** captures who you are — your patterns, values, fears, and stable behaviors built up over time
- **Memory** captures what's on your mind — short-term tracks recent context (90 days), long-term preserves important events indefinitely

Together, these give agents the context to anticipate what you need before you ask.

## Unified Agent Architecture

Every agent in Euno (including the user) has the same structure:

- **Profile** — Identity and behavioral patterns that evolve over time
- **Short-term Memory** — 90-day rolling window of active context
- **Long-term Memory** — Indefinite archive of important events (organized by year)
- **Synthesis** — Internal process that manages memory and profile updates
- **Tools** — Capabilities defined by config

This unified structure means every agent can maintain and evolve its own profile and memory.

## Synthesis

Synthesis is an internal process that each agent runs to manage memory and profile updates. It replaces the deprecated Profiler, Archivist, and Adaptor agents with a built-in capability.

### Two Phases

**Append Phase** (lightweight, after each conversation)
- Runs automatically after each `chat()` call
- Uses LLM to extract noteworthy items from the conversation
- Adds new items to short-term memory
- Fast and non-blocking

**Consolidate Phase** (heavy, on daily trigger)
- Runs on configurable trigger (default: `time:evening`)
- Analyzes patterns in short-term and long-term memory
- Graduates important items from short-term to long-term
- Updates the agent's profile based on observed patterns
- Creates historical profile snapshots at year boundaries

### Configuration

Each agent can configure synthesis in their `config.json`:

```json
{
  "synthesis": {
    "enabled": true,
    "append_enabled": true,
    "consolidate_trigger": "time:evening"
  }
}
```

### Logs

Synthesis operations are logged to `data/system/logs/synthesis/{date}.jsonl`.

## Profile

The Profile captures who an agent is based on observed behavior. It's built from Long-term Memory by the Synthesis process and updated over time.

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
   Most life is spent exploiting known, safe strategies for stability (≈90%), while a smaller portion is reserved for bounded, reversible exploration (≈10%) to discover new options and maintain future safety. Pressure can support growth, but only when it preserves agency, dignity, and integration.

### Profile Schema

Profiles capture behavioral patterns and evolve based on long-term memory.

**User Profile** (`data/agents/user/profile.md`)
1. Biographical Information (name, addresses, phone numbers, etc.)
2. Wants and Fears (patterns of behavior that uncover desires and fears)
3. Stable Attractors (patterns the person returns to)
4. Notable Events and Actions (either because they are consistent or surprising)
5. Influences (people, places, books, activities, entertainment, trips, experiences, etc.)
6. Interests (goals, projects, work, hobbies, entertainment)
7. Summary of changes from previous years

**AI Agent Profile** (`data/agents/{id}/profile.md`)
1. Purpose — What the agent does
2. Behavioral Rules — Must/must not constraints
3. Voice — Communication style
4. How I Work — Specific workflows

**Historical Profiles** (`data/agents/{id}/profile.{yyyy}.md`)

Year-specific snapshots using the same schema. Historical profiles allow tracking how agents change over time.

## Memory

Memory has two forms: short-term for active context and long-term for permanent records.

### Short-term Memory

Tracks what's currently on an agent's mind — the people, places, things, and ideas mentioned recently. Stored in `data/agents/{id}/memory/short-term.jsonl`.

**Entry Schema:**
- `id` — Unique identifier (e.g., `mem-abc12345`)
- `date_mentioned` — When the item was first mentioned
- `date_expected` — Optional date when this becomes relevant
- `type` — Category of the item
- `short_description` — Brief description

**Types:**
- `person` — Someone to follow up with, check on, or reconnect with
- `place` — A location relevant to upcoming plans
- `thing` — Physical items, purchases, or objects of interest
- `goal` — Fitness goals, habits, skills being developed
- `concern` — Health issues, relationship tensions, work challenges
- `idea` — Projects to explore, insights, books, social media threads

**Expiration:**
Entries expire 90 days after `date_mentioned`. Expired entries are archived to long-term memory.

**How Agents Use Short-term Memory:**
- Accessed via `list_memory` tool (not auto-injected)
- The Synthesis append phase automatically adds items when noteworthy
- Agents can manually add items using `add_memory` tool
- The Curator agent checks items (especially those with approaching `date_expected`) during morning reviews
- Agents use it to ask relevant follow-up questions and notice when something needs attention

### Long-term Memory

Chronological archive of important events, preserved indefinitely. Organized by year: `data/agents/{id}/memory/long-term/{yyyy}/{yyyy-mm-dd}.md`.

**Purpose:**
- Preserve lived experience with high fidelity
- Source of truth for constructing Profiles
- Enable agents to reference past events

**How Agents Use Long-term Memory:**
- Written by Synthesis consolidate phase
- Written by agents using `write_long_term_memory` tool
- Read by Synthesis for profile construction
- Any agent can read it for historical context

## Agent Profiles

Agents have specific roles and behaviors to create and leverage the user's profile and memory to form the Euno system.

Each agent has:
- Config: `data/agents/{id}/config.json`
- Profile: `data/agents/{id}/profile.md`
- Synthesis: Internal process for memory/profile management

All agents share ethical constraints: no coercion, no manipulation, no bypassing resistance. Agents prioritize agency, dignity, and coherence.

### Curator

Explores **integrable opportunities** and allocates **scarce attention**.

- Filters opportunities through the Profile first
- Decides what deserves attention given capacity, strain, and context
- Tracks energy dimensions: physical, mental, emotional, social
- Surfaces fewer, higher-fit opportunities at better times
- Defers novelty during high strain; introduces surprise only when safe

### Friend

Supports **thinking and decision-making** without threatening identity coherence.

- The voice the user interacts with
- Treats resistance as information, not opposition
- References the Profile when helping with decisions
- Slows down when emotions intensify
- Core promise: help the user remain themselves under pressure

### Worker

Executes **tasks without undermining agency**.

- Checks the Profile before irreversible actions (time, reputation, obligation, relationship)
- Requires explicit affirmation for commitments
- Efficiency serves life only when control and reversibility are preserved
- Never auto-optimizes at the expense of recovery or reflection

## Data Flow

```
Conversations → Synthesis Append → Short-term Memory
                                        ↓
                     Synthesis Consolidate (daily)
                                        ↓
                              Long-term Memory → Profile
```

Short-term memory entries expire and archive to long-term memory after 90 days.
