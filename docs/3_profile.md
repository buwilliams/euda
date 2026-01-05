# Profile Spec

This defines the mechanism that constructs a person's profile. The goal of Euno is to be "a personal intelligence that anticipates you." We achieve this goal by having a clear understanding of who the user is so that all Agent behaviors are shaped by this understanding of the person. This understanding starts with the cognitive core which in turns results in an annual profile and current profile.

## Cognitive Core

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

## Profile

The profile captures the cognitive core.

**Current Profile** (profile.current.md)
1. Biographical Information (name, addresses, phone numbers, etc.)
2. Wants and Fears (patterns of behavior that uncover desires and fears)
3. Stable Attractors (patterns the person returns to)
4. Notable Events and Actions (either because they are consistent or surprising)
5. Influences (people, places, books, activities, entertainment, trips, experiences, etc.)
6. Interests (goals, projects, work, hobbies, entertainment)
7. Summary of changes from previous years

**Historical Profiles** (profile.yyyy.md)

Year-specific snapshots using the same schema as the current profile. Historical profiles allow agents to track how a person changes over time, answer questions about what caused shifts, and distinguish stable attractors from temporary patterns.

## Agent Personas

Agents have specific roles, personas, and behaviors to create and leverage the user's profile to form the Euno system. The agent personas are used in AI API calls as the system_prompt. They always include `0_core.agent.md` and their specific `[number]_[name].agent.md`.

### 0. Core

Defines the **identity model, epistemic rules, and ethical constraints** inherited by all agents.

- Establishes the shared definition of identity as emergent behavioral patterns
- Sets ethical boundaries: no coercion, no manipulation, no bypassing resistance
- Ensures all agents prioritize agency, dignity, and coherence
- Agents may specialize behavior but may not contradict the Core

### 1. Archivist

Preserves **irreversible human signal** with high fidelity.

- Captures lived data before interpretation or compression
- Protects evidence that reveals identity under load
- Preserves verbatim: journals, conversations, boundary statements, emotional expressions
- Outputs raw, annotated logs—memory, not meaning

### 2. Profiler

Constructs the **Profile** from raw Lifelog data.

- Produces profile.current.md with the schema defined above
- Produces historical profiles (profile.yyyy.md) for each year
- Extracts patterns from behavior, not stated preferences
- Detects identity change through rising enforcement cost, narrative ambivalence, exception creation

### 3. Curator

Explores **integrable opportunities** and allocates **scarce attention**.

- Filters opportunities through the Profile first
- Decides what deserves attention given capacity, strain, and context
- Tracks energy dimensions: physical, mental, emotional, social
- Surfaces fewer, higher-fit opportunities at better times
- Defers novelty during high strain; introduces surprise only when safe

### 4. Friend

Supports **thinking and decision-making** without threatening identity coherence.

- The voice the user interacts with
- Treats resistance as information, not opposition
- References the Profile when helping with decisions
- Slows down when emotions intensify
- Core promise: help the user remain themselves under pressure

### 5. Worker

Executes **tasks without undermining agency**.

- Checks the Profile before irreversible actions (time, reputation, obligation, relationship)
- Requires explicit affirmation for commitments
- Efficiency serves life only when control and reversibility are preserved
- Never auto-optimizes at the expense of recovery or reflection

### 6. Adaptor

Refines **agent identities** to better serve this specific user while maintaining the cognitive core.

- Proposes evolution based on user interactions, behaviors, and what will promote the user to thrive
- Tracks misalignment between agent behavior and user identity
- Reduces friction and increases trust—never the opposite
- Allows the agents to take on personalities and behaviors that are desired by the user

## Data Flow

```
Raw Data → Archivist → Lifelog → Profiler → Profile
```

## Lifelog

The Lifelog is a chronological archive of raw human data, preserved before interpretation or compression. It is the source of truth for constructing the Profile.

Structure: `data/shared/state/lifelog/yyyy/yyyy-mm-dd.md`

The Lifelog contains one file per day, organized by year. The Archivist writes to it; the Profiler reads from it.