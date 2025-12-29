# Profile Synthesis Prompt

*Instructions for synthesizing a complete profile from biographical data*

## Task

Synthesize a **unified profile** that combines:
1. **Behavioral model** (predictive structure) - Identity Stack sections
2. **Biographical context** (supporting color) - Values, influences, beliefs, relationships

Both inform prediction. The behavioral model provides structure; the biographical context provides color and evidence.

## Prime Questions

Identity emerges through multiple channels. Use all three lenses:

> **What would this person rather suffer than violate?** (Sacrifice)
> **What positions do they hold consistently across time and context?** (Commitment)
> **What do they repeatedly do, build, or return to?** (Pattern)

Sacrifice is strong evidence but not the only evidence. Someone whose life is organized around ideas may reveal identity through consistent intellectual positions, creative output, and defended beliefs—not just interpersonal boundary enforcement.

**Weighting principle**: Evidence from multiple channels reinforces confidence. A belief that is both *stated consistently* AND *defended under pressure* AND *reflected in behavior* is high-confidence. A belief that is only stated once, never tested, carries low weight.

## Input Sources

Read these before extracting:

1. `list_temporal_profiles()` - See available years
2. `get_temporal_profile(year)` for each year - Biographical data
3. `get_evolution()` - Change narrative over time
4. `get_influence_timeline()` - When ideas appeared

## Extraction Process

For each section, ask the extraction question and look for evidence in the biographical data.

### 1. Identity Constraints

**Extraction questions**:
- What has this person sacrificed or refused, even at high cost? (Sacrifice evidence)
- What positions do they defend consistently in writing, conversation, and action? (Commitment evidence)
- What principles appear across multiple life domains? (Cross-domain evidence)

**Evidence types** (in order of weight when isolated, but combine for higher confidence):

1. **Sacrifice/Refusal** - Decisions that cost money, status, relationships, or comfort
2. **Consistent Commitment** - Positions stated repeatedly across time, especially in writing (essays, journals, conversations)
3. **Defended Under Pressure** - Beliefs maintained when challenged or when easier alternatives existed
4. **Cross-Domain Application** - Same principle appearing in parenting, work, relationships, creative output

Look for:
- Boundaries enforced despite pressure (behavioral)
- Refusals that persisted across contexts (behavioral)
- Ideas elaborated in multiple essays or conversations (intellectual)
- Philosophical positions that shape decisions (intellectual + behavioral)
- Creative or professional choices that reflect underlying values (pattern)

**Confidence calibration**:
- **High**: Multiple evidence types, observed across years, tested by cost OR consistently elaborated
- **Medium**: Clear pattern but limited to one domain or evidence type
- **Low**: Stated but untested, or single observation

Format each constraint:
```markdown
- **[Short label]**: [Description of the constraint]
  - Evidence: [pointer to temporal profile or evolution, not excerpt]
  - Evidence type: [sacrifice | commitment | defended | cross-domain]
  - Confidence: [high | medium | low]
  - Last observed: [YYYY or YYYY-MM]
```

If no clear constraints are visible in the data, note: "Insufficient data to infer constraints."

### 2. Failure Modes

**Extraction question**: How does this person predictably break down under stress?

Look for:
- Patterns when overwhelmed (withdrawal, over-control, impulsivity, avoidance)
- Triggers that reliably produce negative responses
- Recovery patterns after breakdown
- Rationalization loops they fall into

Format each failure mode:
```markdown
- **[Trigger] → [Response]**: [Description]
  - Evidence: [pointer]
  - Confidence: [high | medium | low]
  - Last observed: [YYYY or YYYY-MM]
```

### 3. Behavioral Attractors

**Extraction question**: What patterns does this person return to across different contexts?

Look for:
- Habits that persist despite attempts to change
- Default approaches to problems
- Recurring relationship dynamics
- Stable preferences across years
- **Intellectual patterns**: Recurring themes in writing, thinking styles, problem-solving approaches
- **Creative patterns**: What they build, how they build, what projects they return to
- **Learning patterns**: How they acquire and integrate new ideas
- **Communication patterns**: How they explain, persuade, connect

**Domain balance**: Ensure attractors span multiple life domains—interpersonal, intellectual, creative, professional, physical. If all attractors cluster in one domain (e.g., parenting), actively search other domains for patterns.

Format:
```markdown
- **[Pattern name]**: [Description of the stable pattern]
  - Domain: [interpersonal | intellectual | creative | professional | physical | spiritual]
  - Evidence: [pointer]
  - Confidence: [high | medium | low]
  - Last observed: [YYYY or YYYY-MM]
```

### 4. Utility Tradeoff Curves

**Extraction question**: When goals conflict, what does this person sacrifice first?

Look for:
- Choices between competing goods (truth vs. belonging, comfort vs. dignity, speed vs. certainty)
- What they gave up to get something else
- Consistent ordering of priorities under pressure

Format:
```markdown
- **[X] over [Y]**: [Evidence of this tradeoff]
  - Evidence: [pointer]
  - Confidence: [high | medium | low]
  - Last observed: [YYYY or YYYY-MM]
```

### 5. Epistemic Style

**Extraction question**: How does this person handle uncertainty, revision, and authority?

Look for:
- Response to being wrong (defensive, curious, devastated)
- Relationship to expertise and credentials
- Comfort with ambiguity vs. need for closure
- How they change their mind

Format:
```markdown
- **[Aspect]**: [Description]
  - Evidence: [pointer]
  - Confidence: [high | medium | low]
```

### 6. Narrative Identity

**Extraction question**: What story does this person tell about themselves?

Look for:
- Self-descriptions and labels they use
- Aspirational framing ("I want to be...")
- Origin stories they reference
- How they explain their choices to others

Note: This section is **useful for alignment but unreliable for prediction**. People's self-narratives often diverge from their actual behavior.

Format:
```markdown
- **[Self-concept element]**: [Description]
  - Evidence: [pointer]
  - Confidence: [high | medium | low]
```

## Output

After extraction, call `write_private_profile()` with content for each section.

**Important**: Include biographical context within the narrative_identity section or as additional context. The profile should be self-contained—readers shouldn't need separate files to understand who this person is.

Example call:
```
write_private_profile(
    identity_constraints="- **[Label]**: [Description]\n  - Evidence: ...\n  - Confidence: high\n  - Last observed: 2024-11",
    failure_modes="- **[Trigger] → [Response]**: ...",
    behavioral_attractors="- **[Pattern]**: ...",
    utility_tradeoffs="- **[X] over [Y]**: ...",
    epistemic_style="- **[Aspect]**: ...",
    narrative_identity="- **[Self-concept]**: ...\n\n### Biographical Context\n\n**Values**: ...\n**Influences**: ...\n**Key Relationships**: ...\n**Current Life Phase**: ..."
)
```

The Narrative Identity section should include:
1. Self-concept elements (how they see themselves)
2. Biographical context that colors the behavioral predictions:
   - Active values and what they prioritize
   - Key influences (books, thinkers, ideas) shaping their worldview
   - Important relationships and their dynamics
   - Current life phase and major themes

## Principles

- **Multiple evidence channels**: Sacrifice, commitment, and pattern all reveal identity. Weight them together, not exclusively.
- **Consistency builds confidence**: A position stated once is weak; a position stated across years, defended under pressure, and reflected in behavior is strong.
- **Domain balance matters**: If the profile skews heavily toward one life domain (parenting, work, etc.), actively search for evidence in underrepresented domains. A whole person has intellectual, creative, relational, and physical dimensions.
- **Intellectual identity is real**: For people whose lives are organized around ideas, philosophical commitments and creative output are as predictive as interpersonal boundary enforcement.
- **Sparse is honest**: If the data doesn't support a claim, don't make it.
- **Pointers, not excerpts**: Reference sources, don't reproduce them.
- **Unified profile**: One document that gives a complete picture.

## After Extraction

Call `generate_current_profile()` to sync the profile to shared state for other agents.
