# Profile Synthesis Prompt

*Instructions for synthesizing a complete profile from biographical data*

## Task

Synthesize a **unified profile** that combines:
1. **Behavioral model** (predictive structure) - Identity Stack sections
2. **Biographical context** (supporting color) - Values, influences, beliefs, relationships

Both inform prediction. The behavioral model provides structure; the biographical context provides color and evidence.

## Prime Question

> **What would this person rather suffer than violate?**

This anchors the behavioral extraction. You are modeling how they will act, supported by the context of who they are.

## Input Sources

Read these before extracting:

1. `list_temporal_profiles()` - See available years
2. `get_temporal_profile(year)` for each year - Biographical data
3. `get_evolution()` - Change narrative over time
4. `get_influence_timeline()` - When ideas appeared

## Extraction Process

For each section, ask the extraction question and look for evidence in the biographical data.

### 1. Identity Constraints

**Extraction question**: What has this person sacrificed or refused, even at high cost?

Look for:
- Decisions that cost them money, status, relationships, or comfort
- Boundaries they enforced despite pressure
- Refusals that persisted across contexts
- Things they won't do even when it would be advantageous

Format each constraint:
```markdown
- **[Short label]**: [Description of the constraint]
  - Evidence: [pointer to temporal profile or evolution, not excerpt]
  - Confidence: [high | medium | low]
  - Last observed: [YYYY or YYYY-MM]
```

If no clear constraints are visible in the data, note: "Insufficient sacrifice/refusal data to infer constraints."

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

Format:
```markdown
- **[Pattern name]**: [Description of the stable pattern]
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

- **Behavior over belief**: What they do, not what they say they value
- **Sacrifice reveals constraint**: Constraints are proven by cost paid
- **Sparse is honest**: If the data doesn't support a claim, don't make it
- **Pointers, not excerpts**: Reference sources, don't reproduce them
- **Unified profile**: One document that gives a complete picture

## After Extraction

Call `generate_current_profile()` to sync the profile to shared state for other agents.
