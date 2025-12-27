# Public Profile Sharing Preferences

Your preferences for how public profiles are generated.
These preferences guide what information may appear in your public profile.

Edit this file to customize your sharing settings.
Preferences here **override defaults** in the redaction policy.
Preferences here **cannot override hard constraints** in the profile contract.

---

## Location Specificity

How specific may location information be in your public profile?

Options:
- `none` — No location information
- `country` — Country only (e.g., "United States")
- `region` — Region/state (e.g., "US Southeast")
- `city` — City level (e.g., "Atlanta area")

```json
{ "location_specificity": "region" }
```

---

## Time Specificity

How specific may temporal information be?

Options:
- `decade` — "In the 2020s..."
- `multi-year` — "In the mid-2020s..."
- `year` — "In 2024..."
- `none` — No temporal markers

```json
{ "time_specificity": "multi-year" }
```

---

## Failure Modes

May failure modes and stress patterns appear in public profiles?

Options:
- `yes` — Include failure modes (generalized)
- `no` — Omit failure modes entirely
- `mild-only` — Only include mild/common patterns

```json
{ "include_failure_modes": "no" }
```

---

## Strain and Struggle

May references to difficulty, strain, or struggle appear?

Options:
- `yes` — May reference challenges
- `no` — Omit all struggle references
- `past-only` — Only past struggles, framed as resolved

```json
{ "include_strain": "past-only" }
```

---

## Proper Nouns

May proper nouns appear in public profiles?

Options:
- `none` — No proper nouns (people, places, organizations)
- `places-only` — Geographic proper nouns only
- `professional-only` — Professional/public figures only
- `all` — All proper nouns permitted

Note: Names of private individuals are never permitted regardless of this setting.

```json
{ "proper_nouns": "none" }
```

---

## Professional Details

May professional information appear?

Options:
- `none` — No professional information
- `domain-only` — General field/domain only
- `role-level` — Role type without employer
- `full` — Full professional context

```json
{ "professional_details": "domain-only" }
```

---

## Evidence Pointers

May evidence pointers (references to source files) appear?

Options:
- `yes` — Include evidence pointers
- `no` — Omit evidence pointers
- `category-only` — Category references only (e.g., "lifelog/")

```json
{ "evidence_pointers": "no" }
```

---

## Tone and Audience

Describe the intended tone and audience for your public profile.
This guides how the LLM writes the public profile content.

```json
{
  "tone": "professional and neutral",
  "audience": "colleagues and professional contacts"
}
```

---

## Custom Exclusions

List specific topics or patterns that should never appear in your public profile,
even if they would otherwise be permitted by default settings.

```json
{
  "custom_exclusions": [
    "family relationships",
    "health patterns",
    "financial behaviors"
  ]
}
```

---

## Custom Inclusions

List specific topics or patterns that you explicitly permit in your public profile,
even if they would otherwise be generalized or omitted by default.

Note: Custom inclusions cannot override hard constraints in the profile contract.

```json
{ "custom_inclusions": [] }
```

---

## Notes

Any additional notes or context for public profile generation.
The LLM will consider these when composing your public profile.

```
No additional notes.
```
