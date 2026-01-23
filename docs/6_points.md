# Contribution Points

The points system tracks and rewards contributions to Euno. Each contributor has a markdown file in [contrib/](../contrib/) recording their work.

## Purpose

- Contributors can see their recorded work
- Point allocations are transparent
- Early contributions are preserved for retroactive rewards at Gate 4

See the [Operating Agreement](6_operating-agreement.md) for how contribution points translate to bonus pool distributions.

## File Format

Each contributor has a file named `firstname-lastname.md` in [contrib/](../contrib/):

```markdown
# Firstname Lastname

- [yyyy-mm-dd][points] - Description of contribution
- [yyyy-mm-dd][points] - Description of contribution
```

Entries are ordered by date descending (most recent first).

## Philosophy

Points reflect **value delivered**, not effort expended. With AI-assisted coding, the old metrics (lines of code, hours spent) are meaningless. What matters is:

- **Impact on the vision** — Does this move Euno closer to being a personal intelligence that anticipates you?
- **Value to the user** — Does this make someone's life better, easier, or more delightful?

A single insight that reshapes how we think about a problem can be worth more than a month of feature work. Using the system daily and uncovering friction is as valuable as building new capabilities.

## Point Values

- **5** — Fix a bug, improve docs, add a small feature, create marketing content
- **10** — Identify a usability problem through real usage, ship a useful feature, write a guide, bring in a new contributor
- **20** — Discover a pattern of friction across the system, build a significant feature, design a better interaction pattern, branding work that improves perception, close a small sales deal, bring in a new paying user, fix-frenzy (fix many bugs in one push), usability sweep (identify many problems through focused testing)
- **30** — Surface a fundamental flaw in the UX or architecture, ship a major capability, ideation that reshapes how we approach a problem, close a significant sales deal, marketing that drives measurable growth
- **50** — Invent an approach that fundamentally advances Euno, discover something that changes our direction, ship a breakthrough feature, ideation that produces a step-change for the user or vision, bring in investment capital

Points are assigned by repository administrators during PR review. When in doubt, ask: "How much closer does this bring us to the vision?"

## How Points Work

**Gates 1-3:** Points are tracked but not paid out. The reward is the trophy—something to put on resumes, talk about, and show off.

**Gate 4+:** Quarterly bonus pool begins.
- Each quarter, Buddy determines a bonus pool from his share of profits
- If there's no profit, there's no bonus pool that quarter
- Pool is distributed based on contribution points
- Your share = your points / total points

Points are retroactively assigned for contributions made before Gate 4, so early contributors accumulate points from the start.

**Note:** Buddy does not participate in the contribution points system. As primary owner, his compensation comes from ownership, not the bonus pool.

## Checking Your Points

```bash
uv run euno points           # Show all contributors
uv run euno points logan     # Filter by name (fuzzy match)
```

## Related Documents

- [Contributing Guide](4_contribute.md) — How to contribute
- [Business Plan](2_business-plan.md) — Vision and growth gates
- [Operating Agreement](6_operating-agreement.md) — Ownership, rewards, and governance
