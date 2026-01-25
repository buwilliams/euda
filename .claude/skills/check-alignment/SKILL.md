---
name: check-alignment
description: Check consistency between docs, specs, tests, and code. Reports drift without making changes.
allowed-tools: Read, Grep, Glob, Task
argument-hint: [entity-name]
---

# Check Alignment: Detect Drift

You are auditing Euno's alignment across the documentation hierarchy:
**docs → specs → tests → code**

This is a READ-ONLY operation. Report findings but do not make changes.

## Process

### 1. Determine Scope

If $ARGUMENTS is provided, focus on that specific entity (e.g., "Agent", "Topic", "Manager").

If no argument, perform a full alignment check across all core entities.

### 2. Parse Entities from Docs

Read `docs/4_system.md` and extract:
- Entity names (Agent, Topic, Manager, etc.)
- Properties for each entity
- States/enums
- Relationships between entities
- Lifecycle behaviors

Create a mental model of what the system SHOULD be according to docs.

### 3. Check Specs Alignment

For each entity, check the relevant spec file:

| Entity | Spec File |
|--------|-----------|
| Agent | `specs/1_agents.md` |
| Topic | `specs/2_data.md` |
| Manager | `specs/1_agents.md` |
| Memory | `specs/2_data.md` |
| API | `specs/3_backend.md` |
| UI | `specs/4_ux_ui.md` |

Look for:
- Missing entities not mentioned in specs
- Properties in docs not specified in specs
- Behaviors in docs not detailed in specs
- Contradictions between docs and specs

### 4. Check Tests Alignment

Search for test files related to each entity:
```
tests/test_agent*.py
tests/test_topic*.py
tests/test_manager*.py
```

Look for:
- Entities with no test coverage
- Properties not tested
- State transitions not tested
- Behaviors documented but not tested

### 5. Check Implementation Alignment

For each entity, find the implementation:

| Entity | Implementation |
|--------|----------------|
| Agent | `src/agent/agent.py` |
| Manager | `src/agent/manager.py` |
| Topic | `src/llms/tools/data/topics.py`, `data/topics/db.sqlite` schema |
| Memory | `src/agent/memory.py`, `src/llms/tools/data/memory.py` |

Look for:
- Properties in specs not in code
- States in specs not in code
- Behaviors in specs not implemented
- Code that contradicts specs

### 6. Generate Report

Output a structured report:

```markdown
# Alignment Report

**Scope:** [Full / Entity: X]
**Date:** [current date]

## Summary
- Entities checked: N
- Aligned: N
- Drift detected: N

## Findings

### Entity: Agent

#### docs/4_system.md → specs/1_agents.md
- [x] States (enabled/disabled/paused) - aligned
- [ ] Triggers - specs missing trigger format details
- [ ] Cognition - not mentioned in specs

#### specs/1_agents.md → tests/
- [ ] No test for agent state transitions
- [x] Work cycle tested

#### specs/1_agents.md → src/agent/agent.py
- [x] States implemented correctly
- [ ] Missing: identity versioning (identity.[year].md)

### Entity: Topic
[...]

## Recommended Actions

1. **High priority:** [description]
2. **Medium priority:** [description]
3. **Low priority:** [description]

---
Run `/align <file>` to propagate fixes.
```

## Key Files Reference

**Docs:**
- `docs/4_system.md` - Primary entity definitions

**Specs:**
- `specs/1_agents.md` - Agent behavior
- `specs/2_data.md` - Data structures
- `specs/3_backend.md` - API/Backend
- `specs/4_ux_ui.md` - UI patterns

**Tests:**
- `tests/` directory

**Implementation:**
- `src/agent/` - Agent system
- `src/llms/tools/` - Tools
- `src/web/` - API

## Important

- This is READ-ONLY - do not modify any files
- Be thorough but concise in the report
- Prioritize findings by impact
- Note ambiguities where docs/specs are unclear
- If the entity list in docs is incomplete, note that too
