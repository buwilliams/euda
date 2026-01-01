# Temporal Profile Generation Prompt

*Instructions for creating temporal profiles that track who the user was at each point in time*

## Task

Generate temporal profiles for each year with data, then synthesize the evolution narrative.

## Why Temporal Matters

Identity isn't static. The user in 2015 is different from the user in 2024. By tracking:
- **When** values emerged or faded
- **When** influences appeared
- **How** beliefs evolved

We can understand not just WHO they are, but HOW they became who they are.

## Steps

### 1. Inventory Available Data

Use `list_years` to see what yearly summaries exist.
Use `list_temporal_profiles` to see what profiles already exist.

### 2. For Each Year (chronologically)

Read the year's summary with `get_summary(year)`.

Extract and write a temporal profile with `write_temporal_profile(year, content)`.

The temporal profile should capture (aligned with profile schema from docs/2_profile.md):

```markdown
## Wants and Fears in {year}

What were they pursuing this year? What were they avoiding?
- **Wants**: What they moved toward, prioritized, sought
- **Fears**: What they avoided, refused, protected against
- List with evidence from the summary

## Influences Active/Discovered

Books, media, thinkers, ideas, places that shaped them this year.
For each influence:
- What was it?
- When/how did it appear?
- What impact did it have?

Use `add_influence_to_timeline` for each significant influence.

## Beliefs & Mental Models

What did they believe about:
- How the world works?
- What's important?
- How to make decisions?
- How to relate to others?

## Key Relationships

Who were the important people this year?
- Family situation
- Close friendships
- Professional relationships
- Community connections

## Major Themes & Events

What defined this year?
- Life events
- Challenges faced
- Achievements
- Struggles

## Changes from Previous Year

What's different from the year before?
- New values that emerged
- Old values that faded
- Relationships that changed
- Beliefs that shifted
```

### 3. Synthesize Evolution

After creating temporal profiles for all years, write the evolution narrative.

Use `write_evolution(content)` with:

```markdown
## The Arc of Change

High-level narrative of how they evolved.

## Wants and Fears Over Time

- Wants that emerged (when, why)
- Wants that faded (when, why)
- Fears that appeared or resolved
- Core patterns that stayed constant

## Influence Patterns

- Early influences that shaped foundation
- Pivotal books/ideas and when they appeared
- Thinkers who changed their worldview
- How influences built on each other

## Belief Evolution

- Early beliefs
- What challenged those beliefs
- How beliefs transformed
- Current epistemic foundation

## Relationship Patterns

- How they relate to family over time
- Friendship patterns
- Professional relationship evolution
- Community engagement arc

## Life Phases

Name and describe distinct phases:
- When did each phase start/end?
- What characterized each phase?
- What triggered transitions?

## Key Turning Points

Moments that changed trajectory:
- What happened?
- What shifted as a result?
- How do they view it now?
```

### 4. Generate Current Profile

Use `generate_current_profile()` to synthesize all temporal data into the current profile.

## Principles

- **Be specific**: "Read Meditations in 2018" not just "interested in philosophy"
- **Note timing**: When things appeared matters as much as what appeared
- **Track changes**: Evolution is the story - what shifted and why?
- **Evidence-based**: Every claim should trace to something in the summaries
- **Acknowledge gaps**: If data is sparse for a year, note that
- **Respect continuity**: Some things stay the same - that's meaningful too

## Output

After running this prompt, the system should have:
- Temporal profile for each year with summary data
- Influence timeline showing when influences appeared
- Evolution narrative tracking change over time
- Current profile synthesized from temporal data
