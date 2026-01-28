---
name: align
description: Propagate a documentation or spec change downstream through specs, tests, and code. Use after updating docs/ or specs/ files.
allowed-tools: Read, Grep, Glob, Edit, Write, Task
argument-hint: <file-path>
---

# Align: Propagate Changes Downstream

You are helping propagate changes through Euno's top-down workflow:
**docs → specs → tests → code**

The user has updated a file and wants to ensure downstream artifacts are aligned.

## Process

### 1. Understand the Change

Read the file specified in $ARGUMENTS to understand what changed.

If no argument provided, ask: "Which file did you update?"

Identify:
- What entities/concepts were added, modified, or removed?
- What properties or behaviors changed?
- What is the scope of impact?

### 2. Determine Cascade Level

Based on the file type, determine what's downstream:

| Changed File | Check/Update |
|--------------|--------------|
| `docs/*.md` | specs/ → tests/ → src/ |
| `specs/*.md` | tests/ → src/ |
| `tests/` | src/ (if tests reveal implementation gaps) |
| `src/` | Nothing downstream (but warn if docs/specs need updating) |

### 3. Check Each Downstream Level

For each downstream level, read relevant files and identify gaps:

**Specs (specs/*.md)**
- Do specs reflect the entities/properties from docs?
- Are behaviors documented?
- Are constraints specified?

**Tests (tests/)**
- Do tests exist for the entities?
- Are edge cases from specs covered?
- Are state transitions tested?

**Implementation (src/)**
- Does code implement what specs describe?
- Are all properties present?
- Do behaviors match?

### 4. Report Findings

Before making changes, summarize:
```
## Alignment Report for [file]

### Downstream impacts:
- specs/X.md: [needs update / aligned]
- tests/test_X.py: [needs update / missing / aligned]
- src/X.py: [needs update / aligned]

### Proposed changes:
1. [specific change]
2. [specific change]
```

### 5. Make Updates (with confirmation)

Ask: "Should I proceed with these updates?"

Then make the changes, working top-down:
1. Update specs first
2. Update tests
3. Update implementation

After each file, briefly note what was changed.

## Key Euno Files

**Docs (source of truth for concepts):**
- `docs/1_vision.md` - Product vision, core value prop
- `docs/4_system.md` - Entities, properties, lifecycle

**Specs (source of truth for behavior):**
- `specs/1_agents.md` - Agent behavior, triggers, work cycles
- `specs/2_data.md` - Data structures, schemas, file paths
- `specs/3_backend.md` - Server, API, storage
- `specs/4_ux_ui.md` - User experience patterns

**Implementation:**
- `src/agent/` - Agent, Manager, cognition
- `src/llms/tools/` - Tool implementations
- `src/web/` - API routes
- `data/` - Runtime data structures

## Important

- Always read before editing - never assume file contents
- Keep changes minimal and focused
- If a change would be large, break it into steps and confirm each
- Note any ambiguities that need human decision
