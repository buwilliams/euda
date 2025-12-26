# Derive Identity Prompt

*Instructions for uncovering the epistemic core from life summaries*

## Task

Analyze the yearly summaries and derive identity.

## Foundational Focus: Epistemic Core

Epistemic axioms are the deepest layer - the beliefs that GENERATE values and behaviors.
Your task is to uncover the MIND behind the behaviors.

**CRITICAL: Each epistemic entry must include PROVENANCE** - the behavior/scenario
that revealed this belief. Format:

### [Axiom/Model/Tool Name]
**Behavior**: What was observed (specific scenario from summaries)
**Belief/Model/Tool**: The underlying epistemic element
**Reasoning**: How this behavior reveals this belief

## Steps

1. Use get_all_summaries to read all available summaries
2. Use get_all_epistemic to see any existing epistemic data

3. DERIVE EPISTEMIC AXIOMS - Core beliefs that drive decisions:
   - Look for recurring decision patterns and ask: "What belief makes this rational?"
   - Identify statements about reality, knowledge, meaning, human nature, agency
   - Note beliefs about what's true, what's knowable, what matters

   For each axiom, include:
   - The specific behavior/scenario that revealed it
   - The axiom itself
   - How the behavior reveals the axiom

   Use write_axioms to save (include all provenance)

4. DERIVE MENTAL MODELS - Frameworks used for thinking:
   - How do they approach decisions? (expected value, satisficing, heuristics?)
   - How do they think about relationships? (reciprocity, boundaries, attachment?)
   - How do they think about uncertainty? (probability, robustness, optionality?)
   - How do they think about time? (present-focused, future-oriented, legacy?)
   - How do they think about conflict? (confrontation, avoidance, repair?)

   For each model, include provenance showing where it was observed.

   Use write_mental_models to save (include all provenance)

5. DERIVE EPISTEMIC TOOLS - Reasoning methods employed:
   - Do they test beliefs against reality? (falsification)
   - Do they seek to understand opposing views? (steel-manning)
   - Do they reason from fundamentals? (first principles)
   - Do they update based on evidence? (Bayesian updating)
   - Do they think backwards from failure? (inversion)

   For each tool, include provenance showing where it was employed.

   Use write_epistemic_tools to save (include all provenance)

## Derived: Values (from epistemic core)

Values emerge from epistemic axioms applied to life decisions.

6. Derive values at three temporal scopes:

   CURRENT VALUES (rolling year):
   - What matters right now based on recent patterns
   - Connect to underlying axioms where possible

   PHASE VALUES (life phase):
   - Values characteristic of this phase of life
   - Name the phase if evident

   LIFETIME VALUES (enduring):
   - Values that persist across phases
   - These often map closely to axioms

   Use write_current_values, write_phase_values, write_lifetime_values

## Derived: Behavioral Patterns (reveals operative axioms)

7. Examine summaries for behavioral patterns that reveal which axioms
   are actually operative (vs just professed):

   - Daily rhythms and routines
   - Decision-making patterns
   - Communication style
   - How they actually spend time vs what they say matters
   - Stress responses (what do they do under pressure?)

   Use write_behaviors to record patterns

## Generate Profile

8. Use generate_profile to create a consolidated view with the new hierarchy.

## Principles

- EPISTEMIC AXIOMS ARE FOUNDATIONAL - they generate values and behaviors
- Every belief should have PROVENANCE - the behavior that revealed it
- Ask: "What belief would make this behavior rational?"
- Values derive from axioms applied to life
- Behaviors reveal which axioms are actually operative
- Current epistemic state trumps historical - minds evolve
- Plain language, not jargon
- Let patterns emerge, don't force structure
