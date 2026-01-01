# Profile Extraction Prompt

*Instructions for extracting a complete profile from lifelog data*

## Task

Extract a **profile** from the user's lifelog data following the schema defined in the cognitive core. The profile captures who the person is through their patterns of behavior, not through stated preferences or aspirations.

## Cognitive Core Principles

Remember:
- Identity is the pattern of **stable attractors** over time
- Attractors form through repeated exploitation of strategies that work
- The self-model (narrative) is layered on top of behavior and may be inaccurate
- Focus on what the person **does**, especially under stress and constraint

## Input Sources

Read these before extracting:

1. `list_temporal_profiles()` - See available years
2. `get_temporal_profile(year)` for each year - Yearly data
3. `get_evolution()` - Change narrative over time
4. `get_influence_timeline()` - When influences appeared

## Profile Schema

Extract each section with evidence citations and confidence levels.

### 1. Biographical Information

Basic facts about the person.

**Extract**: Name, location, occupation, family structure, key dates.

Format:
```markdown
- **Name**: [name if known]
- **Location**: [current location]
- **Occupation**: [current role/work]
- **Family**: [key relationships - spouse, children, etc.]
- **Key dates**: [important life events with dates]
```

Note: Only include what is evidenced in the data. Mark unknowns explicitly.

### 2. Wants and Fears

Patterns of behavior that reveal what the person pursues and avoids.

**Extraction questions**:
- What does this person consistently move toward? (wants)
- What does this person consistently avoid or refuse? (fears)
- What has this person sacrificed to get or avoid something? (strong evidence)

Look for:
- Repeated choices that reveal underlying desires
- Boundaries that reveal what they protect
- Refusals that reveal what they won't compromise
- Emotional reactions that reveal what matters

Format each:
```markdown
**Wants**
- **[Want]**: [Description of what they pursue]
  - Evidence: [pointer to temporal profile or lifelog]
  - Confidence: [high | medium | low]

**Fears**
- **[Fear]**: [Description of what they avoid]
  - Evidence: [pointer]
  - Confidence: [high | medium | low]
```

### 3. Stable Attractors

Patterns the person returns to across time and context, especially under stress.

**Extraction questions**:
- What does this person reliably return to when stressed?
- What habits persist despite attempts to change?
- What default approaches do they use across different domains?

Look for:
- Coping mechanisms that appear repeatedly
- Problem-solving approaches used across contexts
- Relationship patterns that recur
- Routines and rituals that persist

Format each:
```markdown
- **[Attractor name]**: [Description of the pattern]
  - Domain: [interpersonal | intellectual | professional | physical | creative | spiritual]
  - Evidence: [pointer to temporal profiles showing pattern across time]
  - Confidence: [high | medium | low]
  - Last observed: [YYYY or YYYY-MM]
```

**Confidence calibration**:
- High: Pattern observed across multiple years and contexts
- Medium: Pattern clear but limited to one domain or time period
- Low: Single observation or stated but not demonstrated

### 4. Notable Events and Actions

Events that are significant because they are consistent with patterns OR surprising departures from them.

**Extraction questions**:
- What actions confirm the stable attractors?
- What actions were surprising or out of character?
- What turning points changed the person's trajectory?

Format each:
```markdown
- **[Date]: [Event/Action]**
  - Significance: [consistent | surprising | turning point]
  - What it reveals: [interpretation]
  - Evidence: [pointer]
```

### 5. Influences

People, places, ideas, and experiences that have shaped the person.

**Extract**: Books, thinkers, mentors, places, activities, media, experiences, communities.

Format:
```markdown
**People**
- **[Name]**: [Relationship and influence]
  - When: [time period]
  - Evidence: [pointer]

**Ideas/Books**
- **[Title/Concept]**: [How it influenced them]
  - When: [time period]
  - Evidence: [pointer]

**Places**
- **[Place]**: [Significance]
  - When: [time period]

**Activities/Practices**
- **[Activity]**: [Role in their life]
  - When: [time period]
  - Evidence: [pointer]
```

### 6. Interests

Current goals, projects, work, hobbies, and entertainment.

**Extract**: What they're actively engaged with now.

Format:
```markdown
**Work/Professional**
- [Current projects and goals]

**Personal Projects**
- [Side projects, creative work, learning]

**Hobbies/Entertainment**
- [Regular activities for enjoyment]

**Goals**
- [Stated or implied objectives]
```

### 7. Summary of Changes

How the person has evolved from previous years.

**Extract**: Key changes from the evolution narrative.

Format:
```markdown
## Changes from Previous Years

**What emerged**: [New patterns, values, or behaviors]

**What faded**: [Patterns that diminished or disappeared]

**What stayed constant**: [Core patterns that persist]

**Current phase**: [Brief description of where they are now]
```

## Output

After extraction, call `write_private_profile()` with content for each section:

```
write_private_profile(
    biographical_info="- **Name**: ...\n- **Location**: ...",
    wants_and_fears="**Wants**\n- ...\n\n**Fears**\n- ...",
    stable_attractors="- **[Pattern]**: ...",
    notable_events="- **[Date]: [Event]**: ...",
    influences="**People**\n- ...\n\n**Ideas**\n- ...",
    interests="**Work**\n- ...\n\n**Hobbies**\n- ...",
    changes_summary="**What emerged**: ...\n\n**What stayed constant**: ..."
)
```

Then call `generate_current_profile()` to sync the profile to shared state.

## Principles

- **Behavior over statements**: What they do matters more than what they say
- **Patterns over incidents**: Look for repetition across time and context
- **Evidence required**: Every claim needs a pointer to source data
- **Sparse is honest**: If the data doesn't support a claim, don't make it
- **Confidence calibration**: Be explicit about certainty levels
