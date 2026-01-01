# Public Sharing Policy — Euno

This document describes what kinds of information are appropriate for public profiles.

It is written for humans and LLMs alike.
It is NOT code logic—it is principles for judgment.

---

## Purpose of Public Profiles

A public profile is a **safe structural representation** of a person.

Its purpose:
- To communicate patterns and tendencies without exposing raw data
- To enable alignment in collaboration without requiring vulnerability
- To share who someone is without revealing what they've lived

A public profile is an **intentional composition**, not a filtered copy.

---

## What May Appear in Public Profiles

### Appropriate for Sharing

**Structural patterns**
- Behavioral tendencies described abstractly
- Recurring themes without specific instances
- General approaches to problems, relationships, or decisions

**Generalized values and beliefs**
- What matters to the person, in broad terms
- Epistemic style (how they think, not what they've concluded)
- Priorities and tradeoffs at an abstract level

**Non-identifying context**
- General life phase (e.g., "early career," "raising young children")
- Broad geographic region if relevant (e.g., "based in the US South")
- Professional domain without employer specifics

**Skill and competency patterns**
- Areas of developed expertise
- Learning approaches and preferences
- Work style tendencies

---

## What Must Never Appear in Public Profiles

### Absolutely Forbidden

**Raw source material**
- Diary entries, journal excerpts, or unprocessed notes
- Message transcripts or conversation logs
- Email content or correspondence
- Voice transcriptions

**Direct quotes**
- Verbatim statements from private contexts
- Memorable phrases that could identify specific moments
- Internal monologue or stream-of-consciousness

**Third-party information**
- Names of family members, friends, colleagues, or partners
- Details about others' lives, health, or circumstances
- Relationship dynamics involving specific people

**Precise identifiers**
- Full name (unless user explicitly permits)
- Addresses or specific locations
- Dates of birth, social security numbers, or account numbers
- Workplace names, job titles that identify employer

**Sensitive domains**
- Medical diagnoses or health conditions
- Financial specifics (income, debt, account balances)
- Legal matters or disputes
- Sexual or romantic details
- Mental health specifics
- Substance use patterns

**Vulnerability markers**
- Specific trauma or painful experiences
- Current struggles described in detail
- Information that could be used to manipulate

---

## Generalization Requirements

When information is borderline, apply these transformations:

### Location
- Private: "Lives at 123 Oak Street, Atlanta, GA"
- Public: "Based in the US Southeast" or omit entirely

### Time
- Private: "On March 15, 2023, experienced..."
- Public: "In the mid-2020s, developed a pattern of..."

### Relationships
- Private: "Conflict with sister Maria over inheritance"
- Public: "Has navigated family disagreements over resources"

### Health
- Private: "Diagnosed with anxiety disorder in 2019"
- Public: "Has developed practices for managing stress" or omit

### Work
- Private: "Fired from TechCorp in Q3 2022"
- Public: "Has experienced career transitions" or omit

### Events
- Private: "Divorce finalized December 2021"
- Public: "Has navigated significant relationship changes"

---

## Evidence Handling

### Pointers Only

Public profiles may reference evidence but never reproduce it.

**Acceptable:**
```markdown
- Evidence: lifelog/2024/
- Evidence: synthesis/behaviors/
```

**Not acceptable:**
```markdown
- Evidence: "I wrote in my journal that I felt..."
- Evidence: From the conversation on March 15: "..."
```

### Confidence Without Exposure

State confidence levels without revealing what produced them:
- "High confidence (multiple observations)"
- "Medium confidence (emerging pattern)"
- "Low confidence (limited data)"

Never: "High confidence because on [date] they said [quote]"

---

## The Test for Inclusion

Before including anything in a public profile, ask:

1. **Would this embarrass the person if read by a stranger?**
   - If yes → omit or generalize

2. **Could this be used to identify a specific moment or person?**
   - If yes → omit or generalize

3. **Does this require context to not be misunderstood?**
   - If yes → omit (public profiles lack context)

4. **Is this structure or story?**
   - Story → omit
   - Structure → may include

5. **Would the person choose to share this?**
   - If uncertain → omit

When in doubt, omit.

---

## User Preferences Override

User preferences (in `share.prefs.current.md`) may:
- Allow more specificity than this policy's defaults
- Restrict what this policy permits
- Enable specific categories (e.g., "professional details OK")

User preferences cannot override **hard constraints** in the profile contract.
If the contract forbids it, user preferences cannot permit it.

---

## Summary

**Public profiles are structural, not narrative.**
**They describe patterns, not events.**
**They point to evidence, never reproduce it.**
**They generalize, abstract, and omit rather than expose.**

The goal: a representation that is **useful for alignment** and **safe for sharing**.
