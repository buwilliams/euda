# Anticipate

Euno is "a personal intelligence that anticipates you." This document defines how we achieve anticipation through two complementary systems: **Profile** and **Memory**.

- **Profile** captures who you are — your patterns, values, fears, and stable behaviors built up over time
- **Memory** captures what's on your mind — short-term tracks recent context (90 days), long-term preserves important events indefinitely

Together, these give agents the context to anticipate what you need before you ask.

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
   Most life is spent exploiting known, safe strategies for stability (~90%), while a smaller portion is reserved for bounded, reversible exploration (~10%) to discover new options and maintain future safety. Pressure can support growth, but only when it preserves agency, dignity, and integration.

### Profile Schema

Profiles capture behavioral patterns and evolve based on long-term memory.

**User Profile:**
1. Biographical Information (name, addresses, phone numbers, etc.)
2. Wants and Fears (patterns of behavior that uncover desires and fears)
3. Stable Attractors (patterns the person returns to)
4. Notable Events and Actions (either because they are consistent or surprising)
5. Influences (people, places, books, activities, entertainment, trips, experiences, etc.)
6. Interests (goals, projects, work, hobbies, entertainment)
7. Summary of changes from previous years

**AI Agent Profile:**
1. Purpose — What the agent does
2. Behavioral Rules — Must/must not constraints
3. Voice — Communication style
4. How I Work — Specific workflows

## Memory

Memory has two forms: short-term for active context and long-term for permanent records.

### Short-term Memory

Tracks what's currently on an agent's mind — the people, places, things, and ideas mentioned recently.

**Types:**
- `person` — Someone to follow up with, check on, or reconnect with
- `place` — A location relevant to upcoming plans
- `thing` — Physical items, purchases, or objects of interest
- `goal` — Fitness goals, habits, skills being developed
- `concern` — Health issues, relationship tensions, work challenges
- `idea` — Projects to explore, insights, books, social media threads

**How it works:**
- Entries expire 90 days after mention
- Expired entries archive to long-term memory
- Synthesis automatically adds items from conversations
- Agents use it for follow-up questions and noticing what needs attention

### Long-term Memory

Chronological archive of important events, preserved indefinitely.

**Purpose:**
- Preserve lived experience with high fidelity
- Source of truth for constructing Profiles
- Enable agents to reference past events

## Data Flow

```
Conversations → Synthesis Append → Short-term Memory
                                        ↓
                     Synthesis Consolidate (daily)
                                        ↓
                              Long-term Memory → Profile
```

Short-term memory entries expire and archive to long-term memory after 90 days.
