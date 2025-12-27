# Governance — Profiles & Agent Responsibilities (Euno)

This document defines **who is allowed to update profiles**, **how profile data flows through the system**, and **how agents must use private vs public profiles**.

Its purpose is to prevent:
- profile corruption by competing agents
- accidental leakage of private data
- silent drift in how “identity” is modeled
- role confusion in a multi-agent system

This document is normative. All agents must comply.

---

## Core Principle

**Profiles are edited by one agent, informed by many.**

- Profiles are **authoritative artifacts**, not shared scratchpads.
- Most agents *observe* and *signal*.
- One agent *synthesizes* and *writes*.

---

## Profile Types (Recap)

### Private Profile
- Internal model of the user
- Source of truth for anticipation and personalization
- May contain sensitive, vulnerable, or identifying information
- Files:
  - `profile.current.md`
  - `profile.YYYY.md`

### Public Profile
- Intentionally shareable representation
- Derived under explicit principles and user preferences
- Safe for external use
- Files:
  - `profile.public.current.md`
  - `profile.public.YYYY.md`

Public profiles are **not redacted private profiles**.
They are **separate artifacts**, composed intentionally.

---

## Write Authority (Who Can Modify What)

### Synthesis Agent (The Keeper)
**Sole authority for writing private profiles.**

May:
- Create and overwrite `profile.current.md`
- Create and overwrite `profile.YYYY.md`

Inputs:
- Summaries
- Lifelog data
- Prior profiles
- Signals from other agents
- Ontology and Profile Contract

Synthesis is the **editor-in-chief** of user identity.

---

### Public Profile Generator
**Sole authority for writing public profiles.**

May:
- Create and overwrite `profile.public.current.md`
- Create and overwrite `profile.public.YYYY.md`

Inputs:
- `profile.current.md` (private)
- `profile.contract.md`
- `redaction.policy.md`
- `share.prefs.current.md`

Public profile generation is **opt-in or explicitly requested**.

---

### Evolution Agent (The Evolver)
**May not write user profiles.**

May:
- Propose changes to agent identities
- Recommend re-synthesis when drift is detected
- Maintain system capability documentation

Evolution modifies *the system*, not *the user*.

---

### All Other Agents
**Must never write profile files.**

They may:
- Read profiles
- Emit structured signals
- Suggest (but not enact) updates

---

## Signal-Based Contribution Model

Agents contribute to profile updates indirectly by emitting **signals**.

Signals are short, structured observations written to a shared signal file:

```json
// data/shared/signals/profile_observations.json
{
  "observations": [
    {
      "id": "obs_20251227_001",
      "agent": "interaction",
      "timestamp": "2025-12-27T10:30:00Z",
      "type": "behavioral_pattern",
      "observation": "User postponed social event citing need for solitude",
      "evidence": "lifelog/2025/2025-12-27.md",
      "confidence": "medium",
      "suggested_update": {
        "section": "Failure Modes",
        "action": "strengthen",
        "pattern": "Withdraws under social saturation"
      }
    }
  ]
}
```

### Signal Types

| Type | Description | Example |
|------|-------------|---------|
| `behavioral_pattern` | Recurring action observed | "Consistently checks messages before bed" |
| `constraint_evidence` | Identity constraint revealed | "Refused opportunity that conflicted with family time" |
| `failure_mode_trigger` | Stress response observed | "Withdrew after conflict with colleague" |
| `value_expression` | Value demonstrated in action | "Chose transparency over comfort in difficult conversation" |
| `change_signal` | Possible identity shift | "Third time questioning long-held belief about X" |

### Signal Lifecycle

1. **Emit**: Agent writes observation to `profile_observations.json`
2. **Accumulate**: Observations collect until Synthesis runs
3. **Consume**: Synthesis reads and clears observations
4. **Integrate**: Synthesis decides whether to update profile

Signals are **suggestions**, not commands. Synthesis has final authority.

---

## Read Authority (Who Can Read What)

### Private Profile Access

Agents with **full private profile access**:
- **Synthesis Agent** — reads and writes
- **Attention Agent** — reads to personalize surfacing
- **Interaction Agent** — reads to maintain conversation coherence
- **Worker Agent** — reads to check constraints before actions

Agents with **no private profile access**:
- **Ingestion Agent** — processes raw data, no identity model needed
- **Summary Agent** — compresses time, does not personalize
- **World Agent** — filters opportunities, uses public profile only
- **Evolution Agent** — modifies system, not user model

### Public Profile Access

All agents may read `profile.public.current.md`.

External systems (APIs, integrations) receive **only public profiles**.

---

## Data Flow Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                             │
│  Lifelog, Summaries, Conversations, Task Results                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     OBSERVATION LAYER                            │
│  Interaction, Attention, Worker emit signals                     │
│  → profile_observations.json                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SYNTHESIS AGENT                               │
│  Sole writer of private profiles                                 │
│  Reads: summaries, signals, prior profiles, contract             │
│  Writes: profile.current.md, profile.YYYY.md                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 PUBLIC PROFILE GENERATOR                         │
│  Sole writer of public profiles (on request)                     │
│  Reads: private profile, contract, policy, preferences           │
│  Writes: profile.public.current.md, profile.public.YYYY.md       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CONSUMERS                                   │
│  Internal: Attention, Interaction, Worker (private)              │
│  External: World, APIs, Integrations (public only)               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Enforcement

### Structural Enforcement

Profile write functions are implemented **only** in:
- `src/tools/synthesis/` — private profile tools
- `src/profile/generate.py` — public profile generation

Other agents do not have access to profile write functions.

### Runtime Checks

Profile write functions verify the caller context:
- Private profile writes: Only from Synthesis Agent context
- Public profile writes: Only via explicit generation pipeline

Unauthorized write attempts are logged and rejected.

---

## Versioning and History

### Private Profiles
- `profile.current.md` — always latest
- `profile.YYYY.md` — snapshot for that year

### Public Profiles
- `profile.public.current.md` — always latest
- `profile.public.YYYY.md` — snapshot for that year

### Immutability Rule

Only the **current year's** snapshot may be overwritten.
Prior years are immutable history.

---

## References

- `data/shared/profile/profile.contract.md` — Profile structure contract
- `data/shared/profile/redaction.policy.md` — Public sharing principles
- `data/profile/share.prefs.current.md` — User sharing preferences
- `data/shared/identity/synthesis.identity.md` — Synthesis Agent identity
